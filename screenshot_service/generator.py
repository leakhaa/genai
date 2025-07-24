"""
Screenshot generation service for WMS automation
"""
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
import seaborn as sns
import dataframe_image as dfi
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from loguru import logger
from database.services import WarehouseDataService

class ScreenshotGenerator:
    """Service for generating screenshots and visual evidence"""
    
    def __init__(self, output_dir: str = "screenshots"):
        """
        Initialize screenshot generator
        
        Args:
            output_dir: Directory to save screenshots
        """
        self.output_dir = output_dir
        self.warehouse_service = WarehouseDataService()
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Set matplotlib style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
        # Configure matplotlib for better screenshot quality
        plt.rcParams['figure.dpi'] = 300
        plt.rcParams['savefig.dpi'] = 300
        plt.rcParams['font.size'] = 10
        plt.rcParams['axes.titlesize'] = 12
        plt.rcParams['axes.labelsize'] = 10
        plt.rcParams['xtick.labelsize'] = 8
        plt.rcParams['ytick.labelsize'] = 8
    
    def generate_resolution_screenshot(
        self,
        issue_id: str,
        issue_data: Dict[str, Any],
        resolution_data: Dict[str, Any]
    ) -> str:
        """
        Generate screenshot showing issue resolution
        
        Args:
            issue_id: Issue ID
            issue_data: Issue details
            resolution_data: Resolution data
            
        Returns:
            Path to generated screenshot
        """
        try:
            issue_type = issue_data.get('issue_type', 'UNKNOWN')
            
            if issue_type == 'ASN_MISSING':
                return self._generate_asn_resolution_screenshot(issue_id, issue_data, resolution_data)
            elif issue_type == 'PO_MISSING':
                return self._generate_po_resolution_screenshot(issue_id, issue_data, resolution_data)
            elif issue_type == 'PALLET_MISSING':
                return self._generate_pallet_resolution_screenshot(issue_id, issue_data, resolution_data)
            elif issue_type == 'QUANTITY_MISMATCH':
                return self._generate_quantity_resolution_screenshot(issue_id, issue_data, resolution_data)
            else:
                return self._generate_generic_resolution_screenshot(issue_id, issue_data, resolution_data)
                
        except Exception as e:
            logger.error(f"Failed to generate resolution screenshot: {e}")
            return None
    
    def _generate_asn_resolution_screenshot(
        self,
        issue_id: str,
        issue_data: Dict[str, Any],
        resolution_data: Dict[str, Any]
    ) -> str:
        """Generate screenshot for ASN resolution"""
        try:
            asn_id = issue_data.get('asn_id')
            asn_data = self.warehouse_service.get_asn_data(asn_id) if asn_id else None
            
            if not asn_data:
                return self._generate_generic_resolution_screenshot(issue_id, issue_data, resolution_data)
            
            # Create figure with subplots
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle(f'ASN Resolution: {asn_id}', fontsize=16, fontweight='bold')
            
            # ASN Summary Table
            summary_data = {
                'Metric': ['ASN ID', 'Vendor', 'Status', 'Total POs', 'Total Pallets', 'Expected Date'],
                'Value': [
                    asn_data['asn_id'],
                    asn_data.get('vendor_name', 'N/A'),
                    asn_data['status'],
                    asn_data['total_pos'],
                    asn_data['total_pallets'],
                    asn_data.get('expected_date', 'N/A')
                ]
            }
            
            summary_df = pd.DataFrame(summary_data)
            ax1.axis('tight')
            ax1.axis('off')
            table1 = ax1.table(cellText=summary_df.values, colLabels=summary_df.columns,
                              cellLoc='left', loc='center', bbox=[0, 0, 1, 1])
            table1.auto_set_font_size(False)
            table1.set_fontsize(9)
            table1.scale(1, 2)
            ax1.set_title('ASN Summary', fontweight='bold')
            
            # PO Status Chart
            po_data = asn_data.get('purchase_orders', [])
            if po_data:
                po_statuses = [po['status'] for po in po_data]
                status_counts = pd.Series(po_statuses).value_counts()
                
                ax2.pie(status_counts.values, labels=status_counts.index, autopct='%1.1f%%')
                ax2.set_title('PO Status Distribution', fontweight='bold')
            else:
                ax2.text(0.5, 0.5, 'No PO Data Available', ha='center', va='center', transform=ax2.transAxes)
                ax2.set_title('PO Status Distribution', fontweight='bold')
            
            # Quantity Analysis
            if po_data:
                po_names = [f"PO {po['po_id']}" for po in po_data[:10]]  # Limit to 10 POs
                total_qtys = [po['total_quantity'] for po in po_data[:10]]
                received_qtys = [po['received_quantity'] for po in po_data[:10]]
                
                x = range(len(po_names))
                width = 0.35
                
                ax3.bar([i - width/2 for i in x], total_qtys, width, label='Total', alpha=0.8)
                ax3.bar([i + width/2 for i in x], received_qtys, width, label='Received', alpha=0.8)
                
                ax3.set_xlabel('Purchase Orders')
                ax3.set_ylabel('Quantity')
                ax3.set_title('Quantity Status by PO', fontweight='bold')
                ax3.set_xticks(x)
                ax3.set_xticklabels(po_names, rotation=45, ha='right')
                ax3.legend()
                ax3.grid(True, alpha=0.3)
            else:
                ax3.text(0.5, 0.5, 'No Quantity Data Available', ha='center', va='center', transform=ax3.transAxes)
                ax3.set_title('Quantity Status by PO', fontweight='bold')
            
            # Resolution Details
            resolution_text = f"""
            Resolution Status: {resolution_data.get('status', 'RESOLVED')}
            Resolved At: {resolution_data.get('resolved_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}
            Action Taken: {resolution_data.get('action', 'System automated resolution')}
            
            Resolution Notes:
            {resolution_data.get('notes', 'ASN has been successfully processed and is now available in the system.')}
            """
            
            ax4.text(0.05, 0.95, resolution_text, transform=ax4.transAxes, fontsize=9,
                    verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))
            ax4.set_xlim(0, 1)
            ax4.set_ylim(0, 1)
            ax4.axis('off')
            ax4.set_title('Resolution Details', fontweight='bold')
            
            # Save screenshot
            filename = f"asn_resolution_{issue_id[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            filepath = os.path.join(self.output_dir, filename)
            
            plt.tight_layout()
            plt.savefig(filepath, bbox_inches='tight', facecolor='white', edgecolor='none')
            plt.close()
            
            logger.info(f"Generated ASN resolution screenshot: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to generate ASN resolution screenshot: {e}")
            return None
    
    def _generate_po_resolution_screenshot(
        self,
        issue_id: str,
        issue_data: Dict[str, Any],
        resolution_data: Dict[str, Any]
    ) -> str:
        """Generate screenshot for PO resolution"""
        try:
            po_id = issue_data.get('po_id')
            po_data = self.warehouse_service.get_po_data(po_id) if po_id else None
            
            if not po_data:
                return self._generate_generic_resolution_screenshot(issue_id, issue_data, resolution_data)
            
            # Create figure
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle(f'PO Resolution: {po_id}', fontsize=16, fontweight='bold')
            
            # PO Summary
            summary_data = {
                'Metric': ['PO ID', 'ASN ID', 'Status', 'Total Quantity', 'Received Quantity', 'Total Pallets'],
                'Value': [
                    po_data['po_id'],
                    po_data.get('asn_id', 'N/A'),
                    po_data['status'],
                    f"{po_data['total_quantity']:.2f}",
                    f"{po_data['received_quantity']:.2f}",
                    po_data['total_pallets']
                ]
            }
            
            summary_df = pd.DataFrame(summary_data)
            ax1.axis('tight')
            ax1.axis('off')
            table1 = ax1.table(cellText=summary_df.values, colLabels=summary_df.columns,
                              cellLoc='left', loc='center', bbox=[0, 0, 1, 1])
            table1.auto_set_font_size(False)
            table1.set_fontsize(9)
            table1.scale(1, 2)
            ax1.set_title('PO Summary', fontweight='bold')
            
            # Quantity Progress
            total_qty = po_data['total_quantity']
            received_qty = po_data['received_quantity']
            remaining_qty = total_qty - received_qty
            
            sizes = [received_qty, remaining_qty] if remaining_qty > 0 else [received_qty]
            labels = ['Received', 'Remaining'] if remaining_qty > 0 else ['Received']
            colors = ['#2ecc71', '#e74c3c'] if remaining_qty > 0 else ['#2ecc71']
            
            ax2.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            ax2.set_title('Quantity Progress', fontweight='bold')
            
            # Pallet Details
            pallets = po_data.get('pallets', [])
            if pallets:
                pallet_df = pd.DataFrame(pallets[:10])  # Limit to 10 pallets
                
                # Create pallet status chart
                if 'status' in pallet_df.columns:
                    status_counts = pallet_df['status'].value_counts()
                    ax3.bar(status_counts.index, status_counts.values, alpha=0.8)
                    ax3.set_xlabel('Status')
                    ax3.set_ylabel('Count')
                    ax3.set_title('Pallet Status Distribution', fontweight='bold')
                    ax3.tick_params(axis='x', rotation=45)
                    ax3.grid(True, alpha=0.3)
                else:
                    ax3.text(0.5, 0.5, 'No Pallet Status Data', ha='center', va='center', transform=ax3.transAxes)
                    ax3.set_title('Pallet Status Distribution', fontweight='bold')
            else:
                ax3.text(0.5, 0.5, 'No Pallet Data Available', ha='center', va='center', transform=ax3.transAxes)
                ax3.set_title('Pallet Status Distribution', fontweight='bold')
            
            # Resolution Details
            resolution_text = f"""
            Resolution Status: {resolution_data.get('status', 'RESOLVED')}
            Resolved At: {resolution_data.get('resolved_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}
            Action Taken: {resolution_data.get('action', 'PO reconciliation completed')}
            
            Resolution Notes:
            {resolution_data.get('notes', 'PO has been successfully reconciled and all pallets are accounted for.')}
            """
            
            ax4.text(0.05, 0.95, resolution_text, transform=ax4.transAxes, fontsize=9,
                    verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
            ax4.set_xlim(0, 1)
            ax4.set_ylim(0, 1)
            ax4.axis('off')
            ax4.set_title('Resolution Details', fontweight='bold')
            
            # Save screenshot
            filename = f"po_resolution_{issue_id[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            filepath = os.path.join(self.output_dir, filename)
            
            plt.tight_layout()
            plt.savefig(filepath, bbox_inches='tight', facecolor='white', edgecolor='none')
            plt.close()
            
            logger.info(f"Generated PO resolution screenshot: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to generate PO resolution screenshot: {e}")
            return None
    
    def _generate_quantity_resolution_screenshot(
        self,
        issue_id: str,
        issue_data: Dict[str, Any],
        resolution_data: Dict[str, Any]
    ) -> str:
        """Generate screenshot for quantity mismatch resolution"""
        try:
            po_id = issue_data.get('po_id')
            validation_data = resolution_data.get('validation_results', {})
            
            # Create figure
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle(f'Quantity Mismatch Resolution: {po_id}', fontsize=16, fontweight='bold')
            
            # Validation Summary
            summary_data = {
                'Metric': [
                    'PO ID', 'Validation Status', 'Excel Total', 'Database Total', 
                    'Variance', 'Variance %', 'Records Processed'
                ],
                'Value': [
                    po_id or 'N/A',
                    validation_data.get('status', 'N/A'),
                    f"{validation_data.get('excel_total', 0):.2f}",
                    f"{validation_data.get('database_total', 0):.2f}",
                    f"{validation_data.get('variance', 0):.2f}",
                    f"{validation_data.get('variance_percentage', 0):.2f}%",
                    validation_data.get('total_records', 0)
                ]
            }
            
            summary_df = pd.DataFrame(summary_data)
            ax1.axis('tight')
            ax1.axis('off')
            table1 = ax1.table(cellText=summary_df.values, colLabels=summary_df.columns,
                              cellLoc='left', loc='center', bbox=[0, 0, 1, 1])
            table1.auto_set_font_size(False)
            table1.set_fontsize(9)
            table1.scale(1, 2)
            ax1.set_title('Validation Summary', fontweight='bold')
            
            # Quantity Comparison Chart
            excel_total = validation_data.get('excel_total', 0)
            db_total = validation_data.get('database_total', 0)
            
            categories = ['Excel File', 'Database']
            quantities = [excel_total, db_total]
            colors = ['#3498db', '#e67e22']
            
            bars = ax2.bar(categories, quantities, color=colors, alpha=0.8)
            ax2.set_ylabel('Quantity')
            ax2.set_title('Quantity Comparison', fontweight='bold')
            ax2.grid(True, alpha=0.3)
            
            # Add value labels on bars
            for bar, qty in zip(bars, quantities):
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height + max(quantities)*0.01,
                        f'{qty:.2f}', ha='center', va='bottom', fontweight='bold')
            
            # Variance Analysis
            variance = validation_data.get('variance', 0)
            variance_pct = validation_data.get('variance_percentage', 0)
            
            # Create variance visualization
            if abs(variance_pct) < 0.1:
                color = '#2ecc71'  # Green for good
                status_text = 'PASSED'
            elif abs(variance_pct) < 5.0:
                color = '#f39c12'  # Orange for warning
                status_text = 'WARNING'
            else:
                color = '#e74c3c'  # Red for failed
                status_text = 'FAILED'
            
            # Create a gauge-like visualization
            theta = min(abs(variance_pct) / 10 * 180, 180)  # Scale to 180 degrees max
            ax3.pie([theta, 180-theta], colors=[color, '#ecf0f1'], startangle=0, counterclock=False)
            ax3.add_patch(patches.Circle((0, 0), 0.7, color='white'))
            ax3.text(0, 0, f'{variance_pct:.1f}%\n{status_text}', ha='center', va='center', 
                    fontsize=12, fontweight='bold')
            ax3.set_title('Variance Analysis', fontweight='bold')
            
            # Resolution Details
            resolution_text = f"""
            Resolution Status: {resolution_data.get('status', 'RESOLVED')}
            Resolved At: {resolution_data.get('resolved_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}
            Action Taken: {resolution_data.get('action', 'Quantity reconciliation completed')}
            
            Resolution Notes:
            {resolution_data.get('notes', 'Quantity discrepancy has been identified and corrective actions have been taken.')}
            
            Validation Result: {validation_data.get('notes', 'No additional notes available.')}
            """
            
            ax4.text(0.05, 0.95, resolution_text, transform=ax4.transAxes, fontsize=8,
                    verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
            ax4.set_xlim(0, 1)
            ax4.set_ylim(0, 1)
            ax4.axis('off')
            ax4.set_title('Resolution Details', fontweight='bold')
            
            # Save screenshot
            filename = f"quantity_resolution_{issue_id[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            filepath = os.path.join(self.output_dir, filename)
            
            plt.tight_layout()
            plt.savefig(filepath, bbox_inches='tight', facecolor='white', edgecolor='none')
            plt.close()
            
            logger.info(f"Generated quantity resolution screenshot: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to generate quantity resolution screenshot: {e}")
            return None
    
    def _generate_generic_resolution_screenshot(
        self,
        issue_id: str,
        issue_data: Dict[str, Any],
        resolution_data: Dict[str, Any]
    ) -> str:
        """Generate generic resolution screenshot"""
        try:
            # Create simple resolution summary
            fig, ax = plt.subplots(1, 1, figsize=(12, 8))
            fig.suptitle(f'Issue Resolution: {issue_id[:8]}', fontsize=16, fontweight='bold')
            
            resolution_text = f"""
            ISSUE RESOLUTION SUMMARY
            
            Issue ID: {issue_id}
            Issue Type: {issue_data.get('issue_type', 'N/A')}
            Priority: {issue_data.get('priority', 'N/A')}
            Status: {resolution_data.get('status', 'RESOLVED')}
            
            Original Issue:
            {issue_data.get('user_message', 'No message available')}
            
            Resolution Details:
            Resolved At: {resolution_data.get('resolved_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}
            Action Taken: {resolution_data.get('action', 'Issue has been resolved')}
            
            Resolution Notes:
            {resolution_data.get('notes', 'Issue has been successfully resolved through automated processing.')}
            """
            
            ax.text(0.05, 0.95, resolution_text, transform=ax.transAxes, fontsize=11,
                   verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightcyan', alpha=0.8))
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            
            # Save screenshot
            filename = f"generic_resolution_{issue_id[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            filepath = os.path.join(self.output_dir, filename)
            
            plt.tight_layout()
            plt.savefig(filepath, bbox_inches='tight', facecolor='white', edgecolor='none')
            plt.close()
            
            logger.info(f"Generated generic resolution screenshot: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to generate generic resolution screenshot: {e}")
            return None
    
    def generate_dataframe_screenshot(self, df: pd.DataFrame, title: str, issue_id: str) -> str:
        """Generate screenshot of pandas DataFrame"""
        try:
            filename = f"dataframe_{issue_id[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            filepath = os.path.join(self.output_dir, filename)
            
            # Style the DataFrame
            styled_df = df.style.set_table_attributes('style="font-size: 10px"')\
                             .set_caption(title)\
                             .background_gradient(cmap='Blues', alpha=0.6)
            
            # Export to image
            dfi.export(styled_df, filepath, max_rows=50, max_cols=10)
            
            logger.info(f"Generated DataFrame screenshot: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to generate DataFrame screenshot: {e}")
            return None

# Global screenshot generator instance
screenshot_generator = ScreenshotGenerator()

def generate_resolution_screenshot(issue_id: str, issue_data: Dict[str, Any], resolution_data: Dict[str, Any]) -> str:
    """Convenience function to generate resolution screenshot"""
    return screenshot_generator.generate_resolution_screenshot(issue_id, issue_data, resolution_data)

def generate_dataframe_screenshot(df: pd.DataFrame, title: str, issue_id: str) -> str:
    """Convenience function to generate DataFrame screenshot"""
    return screenshot_generator.generate_dataframe_screenshot(df, title, issue_id)