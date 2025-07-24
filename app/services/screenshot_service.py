"""Screenshot service for generating table images and visualizations."""

import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.colors import LinearSegmentedColormap
from datetime import datetime
from typing import Optional, Dict, Any, List
from loguru import logger

from app.config import settings
from app.models import ValidationResult, ScreenshotConfig


class ScreenshotService:
    """Service for generating screenshots and visualizations."""
    
    def __init__(self):
        # Set matplotlib to use non-interactive backend
        plt.switch_backend('Agg')
        
        # Create screenshots directory
        os.makedirs(settings.screenshots_dir, exist_ok=True)
    
    async def generate_validation_table_screenshot(self, validation_result: ValidationResult, 
                                                 po_id: str, config: ScreenshotConfig = None) -> Optional[str]:
        """Generate screenshot of validation results table."""
        try:
            if config is None:
                config = ScreenshotConfig()
            
            # Create figure and axis
            fig, ax = plt.subplots(figsize=(12, 8))
            ax.axis('tight')
            ax.axis('off')
            
            # Prepare data for table
            table_data = []
            
            # Summary row
            table_data.append([
                "Summary",
                f"SAP: {validation_result.total_pallets_sap} pallets",
                f"DB: {validation_result.total_pallets_db} pallets",
                "✅ Valid" if validation_result.is_valid else "❌ Issues Found"
            ])
            
            # Missing pallets
            if validation_result.missing_pallets:
                table_data.append(["Missing Pallets", "", "", ""])
                for pallet_id in validation_result.missing_pallets[:10]:  # Limit to first 10
                    table_data.append(["", pallet_id, "Missing from DB", "❌"])
                if len(validation_result.missing_pallets) > 10:
                    table_data.append(["", f"... and {len(validation_result.missing_pallets) - 10} more", "", ""])
            
            # Quantity mismatches
            if validation_result.quantity_mismatches:
                table_data.append(["Quantity Mismatches", "", "", ""])
                for mismatch in validation_result.quantity_mismatches[:10]:  # Limit to first 10
                    table_data.append([
                        "",
                        mismatch.pallet_id,
                        f"DB: {mismatch.quantity} | SAP: {mismatch.expected_quantity}",
                        "⚠️"
                    ])
                if len(validation_result.quantity_mismatches) > 10:
                    table_data.append(["", f"... and {len(validation_result.quantity_mismatches) - 10} more", "", ""])
            
            # Create table
            if table_data:
                table = ax.table(
                    cellText=table_data,
                    colLabels=["Category", "Pallet ID", "Details", "Status"],
                    cellLoc='left',
                    loc='center',
                    colWidths=[0.2, 0.25, 0.4, 0.15]
                )
                
                # Style the table
                table.auto_set_font_size(False)
                table.set_fontsize(10)
                table.scale(1, 2)
                
                # Color coding
                for i, row in enumerate(table_data):
                    if i == 0:  # Header row
                        for j in range(4):
                            table[(i + 1, j)].set_facecolor('#4CAF50' if validation_result.is_valid else '#f44336')
                            table[(i + 1, j)].set_text_props(weight='bold', color='white')
                    elif "Missing Pallets" in row[0] or "Quantity Mismatches" in row[0]:
                        for j in range(4):
                            table[(i + 1, j)].set_facecolor('#FFC107')
                            table[(i + 1, j)].set_text_props(weight='bold')
                    elif row[3] == "❌":
                        for j in range(4):
                            table[(i + 1, j)].set_facecolor('#FFEBEE')
                    elif row[3] == "⚠️":
                        for j in range(4):
                            table[(i + 1, j)].set_facecolor('#FFF3E0')
            
            # Add title
            plt.title(f'Warehouse Validation Report - PO: {po_id}', 
                     fontsize=16, fontweight='bold', pad=20)
            
            # Add timestamp
            plt.figtext(0.02, 0.02, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 
                       fontsize=8, style='italic')
            
            # Save screenshot
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"validation_table_{po_id}_{timestamp}.{config.format}"
            filepath = os.path.join(settings.screenshots_dir, filename)
            
            plt.savefig(filepath, 
                       dpi=config.dpi, 
                       bbox_inches='tight', 
                       facecolor='white',
                       edgecolor='none')
            plt.close()
            
            logger.info(f"Validation table screenshot saved: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to generate validation table screenshot: {e}")
            plt.close()
            return None
    
    async def generate_summary_chart(self, po_summary: Dict[str, Any], 
                                   config: ScreenshotConfig = None) -> Optional[str]:
        """Generate summary chart for PO."""
        try:
            if config is None:
                config = ScreenshotConfig()
            
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
            
            po_id = po_summary.get('po_id', 'Unknown')
            
            # Chart 1: Pallet Count
            ax1.bar(['Total Pallets'], [po_summary.get('pallet_count', 0)], 
                   color='#2196F3', alpha=0.8)
            ax1.set_title('Total Pallets', fontweight='bold')
            ax1.set_ylabel('Count')
            for i, v in enumerate([po_summary.get('pallet_count', 0)]):
                ax1.text(i, v + 0.1, str(v), ha='center', va='bottom', fontweight='bold')
            
            # Chart 2: Total Quantity
            ax2.bar(['Total Quantity'], [po_summary.get('total_quantity', 0)], 
                   color='#4CAF50', alpha=0.8)
            ax2.set_title('Total Quantity', fontweight='bold')
            ax2.set_ylabel('Units')
            for i, v in enumerate([po_summary.get('total_quantity', 0)]):
                ax2.text(i, v + 0.1, str(v), ha='center', va='bottom', fontweight='bold')
            
            # Chart 3: ASN Count
            ax3.bar(['ASN Count'], [po_summary.get('asn_count', 0)], 
                   color='#FF9800', alpha=0.8)
            ax3.set_title('Unique ASNs', fontweight='bold')
            ax3.set_ylabel('Count')
            for i, v in enumerate([po_summary.get('asn_count', 0)]):
                ax3.text(i, v + 0.1, str(v), ha='center', va='bottom', fontweight='bold')
            
            # Chart 4: Status Summary (placeholder with sample data)
            statuses = ['Active', 'Pending', 'Complete']
            counts = [po_summary.get('pallet_count', 0), 0, 0]  # Simplified for demo
            colors = ['#4CAF50', '#FFC107', '#2196F3']
            
            wedges, texts, autotexts = ax4.pie(counts, labels=statuses, colors=colors, 
                                              autopct='%1.1f%%', startangle=90)
            ax4.set_title('Status Distribution', fontweight='bold')
            
            # Main title
            fig.suptitle(f'Warehouse Summary - PO: {po_id}', 
                        fontsize=16, fontweight='bold')
            
            # Add timestamp
            fig.text(0.02, 0.02, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 
                    fontsize=8, style='italic')
            
            plt.tight_layout()
            
            # Save chart
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"summary_chart_{po_id}_{timestamp}.{config.format}"
            filepath = os.path.join(settings.screenshots_dir, filename)
            
            plt.savefig(filepath, 
                       dpi=config.dpi, 
                       bbox_inches='tight', 
                       facecolor='white',
                       edgecolor='none')
            plt.close()
            
            logger.info(f"Summary chart saved: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to generate summary chart: {e}")
            plt.close()
            return None
    
    async def generate_comparison_table(self, sap_data: List[Dict], db_data: List[Dict], 
                                      po_id: str, config: ScreenshotConfig = None) -> Optional[str]:
        """Generate comparison table between SAP and DB data."""
        try:
            if config is None:
                config = ScreenshotConfig()
            
            # Convert to DataFrames for easier manipulation
            sap_df = pd.DataFrame(sap_data) if sap_data else pd.DataFrame()
            db_df = pd.DataFrame(db_data) if db_data else pd.DataFrame()
            
            # Create comparison data
            comparison_data = []
            
            # Get all unique pallet IDs
            sap_pallets = set(sap_df['pallet_id'].tolist()) if not sap_df.empty else set()
            db_pallets = set(db_df['pallet_id'].tolist()) if not db_df.empty else set()
            all_pallets = sap_pallets.union(db_pallets)
            
            for pallet_id in sorted(list(all_pallets))[:20]:  # Limit to 20 for display
                sap_qty = ""
                db_qty = ""
                status = ""
                
                if pallet_id in sap_pallets:
                    sap_record = sap_df[sap_df['pallet_id'] == pallet_id].iloc[0]
                    sap_qty = str(sap_record.get('quantity', ''))
                
                if pallet_id in db_pallets:
                    db_record = db_df[db_df['pallet_id'] == pallet_id].iloc[0]
                    db_qty = str(db_record.get('quantity', ''))
                
                # Determine status
                if pallet_id not in sap_pallets:
                    status = "DB Only"
                elif pallet_id not in db_pallets:
                    status = "SAP Only"
                elif sap_qty != db_qty:
                    status = "Qty Mismatch"
                else:
                    status = "Match"
                
                comparison_data.append([pallet_id, sap_qty, db_qty, status])
            
            # Create figure
            fig, ax = plt.subplots(figsize=(14, 10))
            ax.axis('tight')
            ax.axis('off')
            
            if comparison_data:
                table = ax.table(
                    cellText=comparison_data,
                    colLabels=["Pallet ID", "SAP Quantity", "DB Quantity", "Status"],
                    cellLoc='center',
                    loc='center',
                    colWidths=[0.3, 0.2, 0.2, 0.3]
                )
                
                # Style the table
                table.auto_set_font_size(False)
                table.set_fontsize(9)
                table.scale(1, 1.5)
                
                # Color coding based on status
                for i, row in enumerate(comparison_data):
                    status = row[3]
                    color = '#FFFFFF'  # Default white
                    
                    if status == "Match":
                        color = '#E8F5E8'  # Light green
                    elif status == "Qty Mismatch":
                        color = '#FFF3E0'  # Light orange
                    elif status in ["DB Only", "SAP Only"]:
                        color = '#FFEBEE'  # Light red
                    
                    for j in range(4):
                        table[(i + 1, j)].set_facecolor(color)
                
                # Header styling
                for j in range(4):
                    table[(0, j)].set_facecolor('#2196F3')
                    table[(0, j)].set_text_props(weight='bold', color='white')
            
            plt.title(f'SAP vs Database Comparison - PO: {po_id}', 
                     fontsize=16, fontweight='bold', pad=20)
            
            # Add legend
            legend_elements = [
                patches.Patch(color='#E8F5E8', label='Match'),
                patches.Patch(color='#FFF3E0', label='Quantity Mismatch'),
                patches.Patch(color='#FFEBEE', label='Missing/Extra')
            ]
            ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1, 1))
            
            # Add timestamp
            plt.figtext(0.02, 0.02, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 
                       fontsize=8, style='italic')
            
            # Save screenshot
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"comparison_table_{po_id}_{timestamp}.{config.format}"
            filepath = os.path.join(settings.screenshots_dir, filename)
            
            plt.savefig(filepath, 
                       dpi=config.dpi, 
                       bbox_inches='tight', 
                       facecolor='white',
                       edgecolor='none')
            plt.close()
            
            logger.info(f"Comparison table screenshot saved: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to generate comparison table: {e}")
            plt.close()
            return None
    
    def cleanup_old_screenshots(self, max_age_hours: int = 48):
        """Clean up old screenshot files."""
        try:
            current_time = datetime.now()
            
            if not os.path.exists(settings.screenshots_dir):
                return
            
            for filename in os.listdir(settings.screenshots_dir):
                file_path = os.path.join(settings.screenshots_dir, filename)
                
                if os.path.isfile(file_path):
                    file_age = current_time - datetime.fromtimestamp(os.path.getctime(file_path))
                    
                    if file_age.total_seconds() > (max_age_hours * 3600):
                        os.remove(file_path)
                        logger.info(f"Cleaned up old screenshot: {file_path}")
        
        except Exception as e:
            logger.error(f"Error during screenshot cleanup: {e}")


# Global screenshot service instance
screenshot_service = ScreenshotService()