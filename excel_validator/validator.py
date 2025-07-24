"""
Excel validation service for WMS automation
"""
import pandas as pd
import openpyxl
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from loguru import logger
from database.services import WarehouseDataService, ExcelValidationService

class ExcelValidator:
    """Service for validating Excel files against database records"""
    
    def __init__(self):
        """Initialize Excel validator"""
        self.warehouse_service = WarehouseDataService()
        self.validation_service = ExcelValidationService()
        
        # Supported file formats
        self.supported_formats = ['.xlsx', '.xls', '.csv']
        
        # Expected column mappings (can be configured)
        self.column_mappings = {
            'po_id': ['PO_ID', 'PO ID', 'Purchase Order', 'PO Number', 'po_id'],
            'pallet_id': ['Pallet_ID', 'Pallet ID', 'Pallet Number', 'pallet_id'],
            'quantity': ['Quantity', 'Qty', 'Amount', 'quantity'],
            'asn_id': ['ASN_ID', 'ASN ID', 'ASN Number', 'asn_id']
        }
    
    def validate_excel_file(
        self,
        file_path: str,
        po_id: str = None,
        asn_id: str = None,
        issue_id: str = None
    ) -> Dict[str, Any]:
        """
        Validate Excel file against database records
        
        Args:
            file_path: Path to Excel file
            po_id: Specific PO ID to validate
            asn_id: Specific ASN ID to validate
            issue_id: Related issue ID
            
        Returns:
            Validation results dictionary
        """
        try:
            # Check file existence and format
            if not os.path.exists(file_path):
                return self._create_error_result(f"File not found: {file_path}")
            
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext not in self.supported_formats:
                return self._create_error_result(f"Unsupported file format: {file_ext}")
            
            # Read Excel file
            df = self._read_excel_file(file_path)
            if df is None:
                return self._create_error_result("Failed to read Excel file")
            
            # Standardize column names
            df = self._standardize_columns(df)
            
            # Validate data structure
            validation_errors = self._validate_data_structure(df)
            if validation_errors:
                return self._create_error_result("Data structure validation failed", validation_errors)
            
            # Perform quantity validation
            if po_id:
                result = self._validate_po_quantities(df, po_id)
            elif asn_id:
                result = self._validate_asn_quantities(df, asn_id)
            else:
                result = self._validate_all_quantities(df)
            
            # Save validation result if issue_id provided
            if issue_id and result:
                self.validation_service.save_validation_result(
                    issue_id=issue_id,
                    filename=os.path.basename(file_path),
                    validation_result=result
                )
            
            logger.info(f"Excel validation completed for {file_path}")
            return result
            
        except Exception as e:
            logger.error(f"Excel validation failed: {e}")
            return self._create_error_result(f"Validation error: {str(e)}")
    
    def _read_excel_file(self, file_path: str) -> Optional[pd.DataFrame]:
        """Read Excel file into pandas DataFrame"""
        try:
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext == '.csv':
                df = pd.read_csv(file_path)
            elif file_ext in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path, engine='openpyxl' if file_ext == '.xlsx' else 'xlrd')
            else:
                return None
            
            logger.debug(f"Read Excel file with {len(df)} rows and {len(df.columns)} columns")
            return df
            
        except Exception as e:
            logger.error(f"Failed to read Excel file {file_path}: {e}")
            return None
    
    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize column names based on mappings"""
        try:
            column_map = {}
            
            for standard_name, possible_names in self.column_mappings.items():
                for col in df.columns:
                    if col.strip() in possible_names:
                        column_map[col] = standard_name
                        break
            
            if column_map:
                df = df.rename(columns=column_map)
                logger.debug(f"Standardized columns: {column_map}")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to standardize columns: {e}")
            return df
    
    def _validate_data_structure(self, df: pd.DataFrame) -> List[str]:
        """Validate Excel data structure"""
        errors = []
        
        # Check for required columns
        required_columns = ['quantity']
        for col in required_columns:
            if col not in df.columns:
                errors.append(f"Missing required column: {col}")
        
        # Check for at least one ID column (PO or ASN)
        if 'po_id' not in df.columns and 'asn_id' not in df.columns:
            errors.append("Missing ID columns: need either 'po_id' or 'asn_id'")
        
        # Check for empty DataFrame
        if df.empty:
            errors.append("Excel file is empty")
        
        # Validate quantity column
        if 'quantity' in df.columns:
            try:
                df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce')
                invalid_quantities = df['quantity'].isna().sum()
                if invalid_quantities > 0:
                    errors.append(f"Found {invalid_quantities} invalid quantity values")
            except Exception as e:
                errors.append(f"Quantity column validation failed: {str(e)}")
        
        return errors
    
    def _validate_po_quantities(self, df: pd.DataFrame, po_id: str) -> Dict[str, Any]:
        """Validate quantities for a specific PO"""
        try:
            # Filter DataFrame for the specific PO
            if 'po_id' in df.columns:
                po_df = df[df['po_id'] == po_id]
            else:
                po_df = df  # Assume all records are for this PO
            
            if po_df.empty:
                return self._create_error_result(f"No records found for PO {po_id} in Excel file")
            
            # Calculate Excel totals
            excel_total = po_df['quantity'].sum()
            excel_records = len(po_df)
            
            # Get database data
            db_data = self.warehouse_service.get_quantity_summary(po_id=po_id)
            if not db_data:
                return self._create_error_result(f"PO {po_id} not found in database")
            
            db_total = db_data['calculated_total']
            variance = excel_total - db_total
            variance_percentage = (variance / db_total * 100) if db_total > 0 else 0
            
            # Determine validation status
            status = self._determine_validation_status(variance_percentage)
            
            # Detailed pallet comparison if available
            pallet_comparison = []
            if 'pallet_id' in po_df.columns:
                pallet_comparison = self._compare_pallets(po_df, db_data.get('pallet_quantities', []))
            
            return {
                'status': status,
                'po_id': po_id,
                'total_records': excel_records,
                'valid_records': len(po_df.dropna()),
                'invalid_records': len(po_df) - len(po_df.dropna()),
                'excel_total': float(excel_total),
                'database_total': float(db_total),
                'variance': float(variance),
                'variance_percentage': float(variance_percentage),
                'pallet_comparison': pallet_comparison,
                'notes': self._generate_validation_notes(variance_percentage, excel_records),
                'validated_at': datetime.utcnow().isoformat(),
                'errors': []
            }
            
        except Exception as e:
            logger.error(f"PO quantity validation failed: {e}")
            return self._create_error_result(f"PO validation error: {str(e)}")
    
    def _validate_asn_quantities(self, df: pd.DataFrame, asn_id: str) -> Dict[str, Any]:
        """Validate quantities for a specific ASN"""
        try:
            # Filter DataFrame for the specific ASN
            if 'asn_id' in df.columns:
                asn_df = df[df['asn_id'] == asn_id]
            else:
                asn_df = df  # Assume all records are for this ASN
            
            if asn_df.empty:
                return self._create_error_result(f"No records found for ASN {asn_id} in Excel file")
            
            # Calculate Excel totals
            excel_total = asn_df['quantity'].sum()
            excel_records = len(asn_df)
            
            # Get database data
            db_data = self.warehouse_service.get_quantity_summary(asn_id=asn_id)
            if not db_data:
                return self._create_error_result(f"ASN {asn_id} not found in database")
            
            db_total = db_data['calculated_total']
            variance = excel_total - db_total
            variance_percentage = (variance / db_total * 100) if db_total > 0 else 0
            
            # Determine validation status
            status = self._determine_validation_status(variance_percentage)
            
            # PO-level breakdown if available
            po_breakdown = []
            if 'po_id' in asn_df.columns:
                po_breakdown = self._analyze_po_breakdown(asn_df)
            
            return {
                'status': status,
                'asn_id': asn_id,
                'total_records': excel_records,
                'valid_records': len(asn_df.dropna()),
                'invalid_records': len(asn_df) - len(asn_df.dropna()),
                'excel_total': float(excel_total),
                'database_total': float(db_total),
                'variance': float(variance),
                'variance_percentage': float(variance_percentage),
                'po_breakdown': po_breakdown,
                'notes': self._generate_validation_notes(variance_percentage, excel_records),
                'validated_at': datetime.utcnow().isoformat(),
                'errors': []
            }
            
        except Exception as e:
            logger.error(f"ASN quantity validation failed: {e}")
            return self._create_error_result(f"ASN validation error: {str(e)}")
    
    def _validate_all_quantities(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate all quantities in the Excel file"""
        try:
            excel_total = df['quantity'].sum()
            excel_records = len(df)
            
            # Group by PO if available
            po_summaries = []
            if 'po_id' in df.columns:
                po_groups = df.groupby('po_id')['quantity'].sum()
                for po_id, total in po_groups.items():
                    db_data = self.warehouse_service.get_quantity_summary(po_id=po_id)
                    if db_data:
                        variance = total - db_data['calculated_total']
                        po_summaries.append({
                            'po_id': po_id,
                            'excel_total': float(total),
                            'database_total': float(db_data['calculated_total']),
                            'variance': float(variance)
                        })
            
            return {
                'status': 'COMPLETED',
                'total_records': excel_records,
                'valid_records': len(df.dropna()),
                'invalid_records': len(df) - len(df.dropna()),
                'excel_total': float(excel_total),
                'po_summaries': po_summaries,
                'notes': f"Validated {excel_records} records across {len(po_summaries)} POs",
                'validated_at': datetime.utcnow().isoformat(),
                'errors': []
            }
            
        except Exception as e:
            logger.error(f"General quantity validation failed: {e}")
            return self._create_error_result(f"Validation error: {str(e)}")
    
    def _compare_pallets(self, excel_df: pd.DataFrame, db_quantities: List[float]) -> List[Dict[str, Any]]:
        """Compare pallet-level quantities between Excel and database"""
        comparison = []
        
        try:
            if 'pallet_id' in excel_df.columns:
                pallet_groups = excel_df.groupby('pallet_id')['quantity'].sum()
                
                for i, (pallet_id, excel_qty) in enumerate(pallet_groups.items()):
                    db_qty = db_quantities[i] if i < len(db_quantities) else 0
                    variance = excel_qty - db_qty
                    
                    comparison.append({
                        'pallet_id': pallet_id,
                        'excel_quantity': float(excel_qty),
                        'database_quantity': float(db_qty),
                        'variance': float(variance),
                        'match': abs(variance) < 0.01  # Allow small floating point differences
                    })
        
        except Exception as e:
            logger.error(f"Pallet comparison failed: {e}")
        
        return comparison
    
    def _analyze_po_breakdown(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Analyze PO-level breakdown within ASN"""
        breakdown = []
        
        try:
            if 'po_id' in df.columns:
                po_groups = df.groupby('po_id')['quantity'].sum()
                
                for po_id, total in po_groups.items():
                    breakdown.append({
                        'po_id': po_id,
                        'excel_total': float(total),
                        'record_count': len(df[df['po_id'] == po_id])
                    })
        
        except Exception as e:
            logger.error(f"PO breakdown analysis failed: {e}")
        
        return breakdown
    
    def _determine_validation_status(self, variance_percentage: float) -> str:
        """Determine validation status based on variance percentage"""
        abs_variance = abs(variance_percentage)
        
        if abs_variance < 0.1:  # Less than 0.1% variance
            return 'PASSED'
        elif abs_variance < 5.0:  # Less than 5% variance
            return 'WARNING'
        else:
            return 'FAILED'
    
    def _generate_validation_notes(self, variance_percentage: float, record_count: int) -> str:
        """Generate human-readable validation notes"""
        abs_variance = abs(variance_percentage)
        
        if abs_variance < 0.1:
            return f"Validation passed. Quantities match within acceptable tolerance. {record_count} records processed."
        elif abs_variance < 5.0:
            return f"Warning: {variance_percentage:.2f}% variance detected. Manual review recommended. {record_count} records processed."
        else:
            return f"Validation failed: {variance_percentage:.2f}% variance detected. Immediate attention required. {record_count} records processed."
    
    def _create_error_result(self, error_message: str, errors: List[str] = None) -> Dict[str, Any]:
        """Create standardized error result"""
        return {
            'status': 'ERROR',
            'total_records': 0,
            'valid_records': 0,
            'invalid_records': 0,
            'excel_total': 0,
            'database_total': 0,
            'variance': 0,
            'variance_percentage': 0,
            'notes': error_message,
            'validated_at': datetime.utcnow().isoformat(),
            'errors': errors or [error_message]
        }
    
    def generate_validation_report(self, validation_result: Dict[str, Any]) -> str:
        """Generate a formatted validation report"""
        try:
            report_lines = [
                "=== EXCEL VALIDATION REPORT ===",
                f"Validation Date: {validation_result.get('validated_at', 'N/A')}",
                f"Status: {validation_result.get('status', 'UNKNOWN')}",
                "",
                "SUMMARY:",
                f"  Total Records: {validation_result.get('total_records', 0)}",
                f"  Valid Records: {validation_result.get('valid_records', 0)}",
                f"  Invalid Records: {validation_result.get('invalid_records', 0)}",
                "",
                "QUANTITY COMPARISON:",
                f"  Excel Total: {validation_result.get('excel_total', 0):.2f}",
                f"  Database Total: {validation_result.get('database_total', 0):.2f}",
                f"  Variance: {validation_result.get('variance', 0):.2f}",
                f"  Variance %: {validation_result.get('variance_percentage', 0):.2f}%",
                "",
                f"NOTES: {validation_result.get('notes', 'No notes available')}",
            ]
            
            # Add errors if any
            errors = validation_result.get('errors', [])
            if errors:
                report_lines.extend([
                    "",
                    "ERRORS:",
                    *[f"  - {error}" for error in errors]
                ])
            
            return "\n".join(report_lines)
            
        except Exception as e:
            logger.error(f"Failed to generate validation report: {e}")
            return f"Report generation failed: {str(e)}"

# Global validator instance
excel_validator = ExcelValidator()

def validate_excel(file_path: str, **kwargs) -> Dict[str, Any]:
    """Convenience function for Excel validation"""
    return excel_validator.validate_excel_file(file_path, **kwargs)