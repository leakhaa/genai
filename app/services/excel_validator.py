"""Excel validation service for processing SAP data files."""

import os
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from loguru import logger

from app.config import settings
from app.models import PalletData, ValidationResult
from app.services.database_service import database_service


class ExcelValidator:
    """Service for validating Excel files from SAP."""
    
    def __init__(self):
        self.supported_formats = ['.xlsx', '.xls', '.csv']
    
    async def validate_excel_file(self, excel_file_path: str, po_id: str) -> ValidationResult:
        """Validate Excel file against database records."""
        try:
            if not os.path.exists(excel_file_path):
                logger.error(f"Excel file not found: {excel_file_path}")
                return ValidationResult(
                    is_valid=False,
                    validation_summary="Excel file not found"
                )
            
            # Read Excel file
            sap_data = await self._read_excel_file(excel_file_path)
            if sap_data is None:
                return ValidationResult(
                    is_valid=False,
                    validation_summary="Failed to read Excel file"
                )
            
            # Get database data
            db_pallets = await database_service.get_pallets_by_po(po_id)
            
            # Perform validation
            return await self._perform_validation(sap_data, db_pallets, po_id)
            
        except Exception as e:
            logger.error(f"Excel validation failed: {e}")
            return ValidationResult(
                is_valid=False,
                validation_summary=f"Validation error: {str(e)}"
            )
    
    async def _read_excel_file(self, file_path: str) -> Optional[pd.DataFrame]:
        """Read Excel file and return DataFrame."""
        try:
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext == '.csv':
                df = pd.read_csv(file_path)
            elif file_ext in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path)
            else:
                logger.error(f"Unsupported file format: {file_ext}")
                return None
            
            # Standardize column names
            df.columns = df.columns.str.lower().str.strip()
            
            # Map common column variations
            column_mapping = {
                'pallet_id': ['pallet_id', 'pallet', 'pallet_number', 'id'],
                'po_id': ['po_id', 'po', 'purchase_order', 'po_number'],
                'asn_id': ['asn_id', 'asn', 'asn_number', 'shipment_id'],
                'quantity': ['quantity', 'qty', 'amount', 'count'],
                'status': ['status', 'state', 'condition'],
                'location': ['location', 'loc', 'warehouse_location', 'position']
            }
            
            # Rename columns based on mapping
            for standard_name, variations in column_mapping.items():
                for variation in variations:
                    if variation in df.columns:
                        df.rename(columns={variation: standard_name}, inplace=True)
                        break
            
            logger.info(f"Successfully read Excel file with {len(df)} rows")
            logger.debug(f"Columns: {list(df.columns)}")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to read Excel file {file_path}: {e}")
            return None
    
    async def _perform_validation(self, sap_data: pd.DataFrame, db_pallets: List, po_id: str) -> ValidationResult:
        """Perform validation between SAP data and database."""
        try:
            # Convert database pallets to dict for easy lookup
            db_pallet_dict = {p.pallet_id: p for p in db_pallets}
            
            # Initialize validation results
            missing_pallets = []
            quantity_mismatches = []
            
            # Check each pallet in SAP data
            for _, row in sap_data.iterrows():
                pallet_id = str(row.get('pallet_id', ''))
                sap_quantity = int(row.get('quantity', 0))
                
                if not pallet_id:
                    continue
                
                # Check if pallet exists in database
                if pallet_id not in db_pallet_dict:
                    missing_pallets.append(pallet_id)
                else:
                    # Check quantity mismatch
                    db_pallet = db_pallet_dict[pallet_id]
                    if db_pallet.quantity != sap_quantity:
                        quantity_mismatches.append(PalletData(
                            pallet_id=pallet_id,
                            po_id=po_id,
                            asn_id=row.get('asn_id'),
                            quantity=db_pallet.quantity,
                            expected_quantity=sap_quantity,
                            status=row.get('status', 'ACTIVE'),
                            location=row.get('location')
                        ))
            
            # Check for pallets in database but not in SAP
            sap_pallet_ids = set(str(row.get('pallet_id', '')) for _, row in sap_data.iterrows() if row.get('pallet_id'))
            db_pallet_ids = set(db_pallet_dict.keys())
            extra_db_pallets = db_pallet_ids - sap_pallet_ids
            
            # Generate validation summary
            is_valid = len(missing_pallets) == 0 and len(quantity_mismatches) == 0 and len(extra_db_pallets) == 0
            
            summary_parts = []
            if missing_pallets:
                summary_parts.append(f"{len(missing_pallets)} pallets missing from database")
            if quantity_mismatches:
                summary_parts.append(f"{len(quantity_mismatches)} quantity mismatches found")
            if extra_db_pallets:
                summary_parts.append(f"{len(extra_db_pallets)} extra pallets in database")
            
            if is_valid:
                validation_summary = "✅ All pallets and quantities match between SAP and database"
            else:
                validation_summary = "❌ Issues found: " + ", ".join(summary_parts)
            
            logger.info(f"Validation completed for PO {po_id}: {validation_summary}")
            
            return ValidationResult(
                is_valid=is_valid,
                missing_pallets=missing_pallets,
                quantity_mismatches=quantity_mismatches,
                total_pallets_sap=len(sap_data),
                total_pallets_db=len(db_pallets),
                validation_summary=validation_summary
            )
            
        except Exception as e:
            logger.error(f"Validation processing failed: {e}")
            return ValidationResult(
                is_valid=False,
                validation_summary=f"Validation processing error: {str(e)}"
            )
    
    async def extract_pallet_data_from_excel(self, excel_file_path: str) -> List[PalletData]:
        """Extract pallet data from Excel file for database insertion."""
        try:
            df = await self._read_excel_file(excel_file_path)
            if df is None:
                return []
            
            pallet_data_list = []
            
            for _, row in df.iterrows():
                pallet_id = str(row.get('pallet_id', ''))
                if not pallet_id:
                    continue
                
                pallet_data = PalletData(
                    pallet_id=pallet_id,
                    po_id=str(row.get('po_id', '')),
                    asn_id=str(row.get('asn_id', '')) if row.get('asn_id') else None,
                    quantity=int(row.get('quantity', 0)),
                    expected_quantity=int(row.get('quantity', 0)),  # Same as quantity for SAP data
                    status=str(row.get('status', 'ACTIVE')),
                    location=str(row.get('location', '')) if row.get('location') else None
                )
                
                pallet_data_list.append(pallet_data)
            
            logger.info(f"Extracted {len(pallet_data_list)} pallet records from Excel")
            return pallet_data_list
            
        except Exception as e:
            logger.error(f"Failed to extract pallet data from Excel: {e}")
            return []
    
    async def generate_comparison_report(self, validation_result: ValidationResult, 
                                       po_id: str) -> str:
        """Generate a detailed comparison report."""
        try:
            report_lines = [
                f"Validation Report for PO: {po_id}",
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "=" * 50,
                "",
                f"Overall Status: {'✅ VALID' if validation_result.is_valid else '❌ ISSUES FOUND'}",
                f"SAP Pallets: {validation_result.total_pallets_sap}",
                f"Database Pallets: {validation_result.total_pallets_db}",
                "",
                validation_result.validation_summary,
                ""
            ]
            
            if validation_result.missing_pallets:
                report_lines.extend([
                    "Missing Pallets (in SAP but not in Database):",
                    "-" * 40
                ])
                for pallet_id in validation_result.missing_pallets:
                    report_lines.append(f"  • {pallet_id}")
                report_lines.append("")
            
            if validation_result.quantity_mismatches:
                report_lines.extend([
                    "Quantity Mismatches:",
                    "-" * 20
                ])
                for mismatch in validation_result.quantity_mismatches:
                    report_lines.append(
                        f"  • {mismatch.pallet_id}: DB={mismatch.quantity}, SAP={mismatch.expected_quantity}"
                    )
                report_lines.append("")
            
            report_content = "\n".join(report_lines)
            
            # Save report to file
            os.makedirs(settings.temp_dir, exist_ok=True)
            report_file = os.path.join(
                settings.temp_dir, 
                f"validation_report_{po_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            )
            
            with open(report_file, 'w') as f:
                f.write(report_content)
            
            logger.info(f"Validation report saved: {report_file}")
            return report_content
            
        except Exception as e:
            logger.error(f"Failed to generate comparison report: {e}")
            return f"Error generating report: {str(e)}"
    
    def cleanup_temp_files(self, max_age_hours: int = 24):
        """Clean up temporary Excel files older than specified hours."""
        try:
            current_time = datetime.now()
            
            for directory in [settings.excel_dir, settings.temp_dir]:
                if not os.path.exists(directory):
                    continue
                
                for filename in os.listdir(directory):
                    file_path = os.path.join(directory, filename)
                    
                    if os.path.isfile(file_path):
                        file_age = current_time - datetime.fromtimestamp(os.path.getctime(file_path))
                        
                        if file_age.total_seconds() > (max_age_hours * 3600):
                            os.remove(file_path)
                            logger.info(f"Cleaned up old file: {file_path}")
            
        except Exception as e:
            logger.error(f"Error during file cleanup: {e}")


# Global Excel validator instance
excel_validator = ExcelValidator()