"""Main warehouse agent orchestration service."""

import uuid
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger

from app.config import settings
from app.models import (
    UserIssueRequest, IssueResolution, IssueStatus, IssueType, 
    ActionType, ScreenshotConfig
)
from app.services.ai_classifier import ai_classifier
from app.services.email_service import email_service
from app.services.database_service import database_service
from app.services.excel_validator import excel_validator
from app.services.screenshot_service import screenshot_service


class WarehouseAgent:
    """Main orchestration service for warehouse issue resolution."""
    
    def __init__(self):
        self.active_resolutions: Dict[str, IssueResolution] = {}
    
    async def process_user_issue(self, user_request: UserIssueRequest) -> IssueResolution:
        """Main entry point for processing user issues."""
        try:
            # Generate unique issue ID
            issue_id = f"WH_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
            
            logger.info(f"Processing new issue {issue_id}: {user_request.message}")
            
            # Step 1: Classify the issue using AI
            classified_issue = await ai_classifier.classify_issue(user_request.message)
            logger.info(f"Issue classified as: {classified_issue.issue_type.value}")
            
            # Create issue resolution tracker
            resolution = IssueResolution(
                issue_id=issue_id,
                original_request=user_request,
                classified_issue=classified_issue,
                status=IssueStatus.PENDING
            )
            
            self.active_resolutions[issue_id] = resolution
            
            # Step 2: Execute the appropriate action based on classification
            await self._execute_resolution_workflow(resolution)
            
            return resolution
            
        except Exception as e:
            logger.error(f"Failed to process user issue: {e}")
            # Create error resolution
            error_resolution = IssueResolution(
                issue_id=f"ERROR_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                original_request=user_request,
                classified_issue=classified_issue if 'classified_issue' in locals() else None,
                status=IssueStatus.FAILED,
                resolution_summary=f"Processing failed: {str(e)}"
            )
            return error_resolution
    
    async def _execute_resolution_workflow(self, resolution: IssueResolution):
        """Execute the resolution workflow based on issue type."""
        try:
            issue = resolution.classified_issue
            
            if issue.action == ActionType.SEND_MAIL_SAP:
                await self._handle_sap_email_workflow(resolution)
            elif issue.action == ActionType.REQUEST_EXCEL:
                await self._handle_excel_request_workflow(resolution)
            elif issue.action == ActionType.VALIDATE_PALLETS:
                await self._handle_pallet_validation_workflow(resolution)
            else:
                await self._handle_generic_workflow(resolution)
                
        except Exception as e:
            logger.error(f"Workflow execution failed for {resolution.issue_id}: {e}")
            resolution.status = IssueStatus.FAILED
            resolution.resolution_summary = f"Workflow execution failed: {str(e)}"
    
    async def _handle_sap_email_workflow(self, resolution: IssueResolution):
        """Handle workflow for ASN/PO missing issues."""
        try:
            issue = resolution.classified_issue
            resolution.add_action("Sending SAP request email")
            resolution.status = IssueStatus.EMAIL_SENT
            
            # Send email to SAP
            success = await email_service.send_sap_request(
                issue_type=issue.issue_type,
                po_id=issue.po_id,
                asn_id=issue.asn_id,
                pallet_id=issue.pallet_id
            )
            
            if not success:
                resolution.status = IssueStatus.FAILED
                resolution.resolution_summary = "Failed to send SAP request email"
                return
            
            resolution.add_action("SAP request email sent successfully")
            resolution.status = IssueStatus.WAITING_RESPONSE
            
            # Monitor for SAP response
            resolution.add_action("Monitoring for SAP response")
            sap_response = await email_service.monitor_sap_response(
                resolution.issue_id, timeout_minutes=30
            )
            
            if sap_response:
                resolution.sap_responses.append(sap_response)
                resolution.add_action(f"SAP response received: {sap_response.response_type}")
                
                if sap_response.response_type == "confirmation":
                    resolution.status = IssueStatus.RESOLVED
                    resolution.mark_resolved(
                        f"✅ {issue.issue_type.value} resolved by SAP. "
                        f"PO: {issue.po_id or 'N/A'}, ASN: {issue.asn_id or 'N/A'}"
                    )
                else:
                    resolution.status = IssueStatus.FAILED
                    resolution.resolution_summary = f"SAP response indicates error: {sap_response.message}"
            else:
                resolution.status = IssueStatus.FAILED
                resolution.resolution_summary = "No response received from SAP within timeout period"
            
            # Send notification to user
            await self._send_user_notification(resolution)
            
        except Exception as e:
            logger.error(f"SAP email workflow failed: {e}")
            resolution.status = IssueStatus.FAILED
            resolution.resolution_summary = f"SAP email workflow failed: {str(e)}"
    
    async def _handle_excel_request_workflow(self, resolution: IssueResolution):
        """Handle workflow for pallet missing issues requiring Excel validation."""
        try:
            issue = resolution.classified_issue
            resolution.add_action("Requesting Excel data from SAP")
            resolution.status = IssueStatus.EMAIL_SENT
            
            # Send email to SAP requesting Excel data
            success = await email_service.send_sap_request(
                issue_type=issue.issue_type,
                po_id=issue.po_id,
                asn_id=issue.asn_id,
                pallet_id=issue.pallet_id
            )
            
            if not success:
                resolution.status = IssueStatus.FAILED
                resolution.resolution_summary = "Failed to send SAP Excel request"
                return
            
            resolution.add_action("Excel request sent to SAP")
            resolution.status = IssueStatus.WAITING_RESPONSE
            
            # Monitor for SAP response with Excel file
            sap_response = await email_service.monitor_sap_response(
                resolution.issue_id, timeout_minutes=45
            )
            
            if sap_response and sap_response.excel_file_path:
                resolution.sap_responses.append(sap_response)
                resolution.add_action("Excel file received from SAP")
                resolution.status = IssueStatus.PROCESSING
                
                # Validate Excel file
                await self._process_excel_validation(resolution, sap_response.excel_file_path)
            else:
                resolution.status = IssueStatus.FAILED
                resolution.resolution_summary = "No Excel file received from SAP"
            
            # Send notification to user
            await self._send_user_notification(resolution)
            
        except Exception as e:
            logger.error(f"Excel request workflow failed: {e}")
            resolution.status = IssueStatus.FAILED
            resolution.resolution_summary = f"Excel request workflow failed: {str(e)}"
    
    async def _handle_pallet_validation_workflow(self, resolution: IssueResolution):
        """Handle workflow for quantity mismatch issues."""
        try:
            issue = resolution.classified_issue
            resolution.add_action("Starting pallet validation workflow")
            
            # First, request Excel data from SAP
            await self._handle_excel_request_workflow(resolution)
            
            # If Excel processing was successful, the validation is already done
            if resolution.status == IssueStatus.RESOLVED:
                return
                
        except Exception as e:
            logger.error(f"Pallet validation workflow failed: {e}")
            resolution.status = IssueStatus.FAILED
            resolution.resolution_summary = f"Pallet validation workflow failed: {str(e)}"
    
    async def _process_excel_validation(self, resolution: IssueResolution, excel_file_path: str):
        """Process Excel file validation and database updates."""
        try:
            issue = resolution.classified_issue
            po_id = issue.po_id or "UNKNOWN"
            
            resolution.add_action("Validating Excel file against database")
            
            # Validate Excel file
            validation_result = await excel_validator.validate_excel_file(excel_file_path, po_id)
            resolution.validation_results = validation_result
            
            resolution.add_action(f"Validation completed: {validation_result.validation_summary}")
            
            # Handle missing pallets
            if validation_result.missing_pallets:
                resolution.add_action(f"Processing {len(validation_result.missing_pallets)} missing pallets")
                
                # Extract pallet data from Excel
                pallet_data = await excel_validator.extract_pallet_data_from_excel(excel_file_path)
                
                # Filter to only missing pallets
                missing_pallet_data = [
                    p for p in pallet_data 
                    if p.pallet_id in validation_result.missing_pallets
                ]
                
                # Insert missing pallets into database
                if missing_pallet_data:
                    insert_success = await database_service.insert_missing_pallets(missing_pallet_data)
                    if insert_success:
                        resolution.add_action(f"Successfully inserted {len(missing_pallet_data)} missing pallets")
                    else:
                        resolution.add_action("Failed to insert missing pallets")
            
            # Handle quantity mismatches
            if validation_result.quantity_mismatches:
                resolution.add_action(f"Processing {len(validation_result.quantity_mismatches)} quantity mismatches")
                
                # Update quantities in database
                quantity_updates = [
                    {
                        'pallet_id': mismatch.pallet_id,
                        'new_quantity': mismatch.expected_quantity
                    }
                    for mismatch in validation_result.quantity_mismatches
                ]
                
                update_success = await database_service.update_pallet_quantities(quantity_updates)
                if update_success:
                    resolution.add_action(f"Successfully updated {len(quantity_updates)} pallet quantities")
                else:
                    resolution.add_action("Failed to update pallet quantities")
            
            # Generate summary and screenshots
            po_summary = await database_service.get_po_summary(po_id)
            
            # Generate validation report
            report_content = await excel_validator.generate_comparison_report(validation_result, po_id)
            
            # Generate screenshots
            screenshot_path = await screenshot_service.generate_validation_table_screenshot(
                validation_result, po_id
            )
            
            # Create audit log
            await database_service.create_audit_log(
                resolution.issue_id,
                "VALIDATION_COMPLETED",
                {
                    "validation_result": validation_result.dict(),
                    "po_summary": po_summary,
                    "excel_file": excel_file_path
                }
            )
            
            # Mark as resolved
            if validation_result.is_valid or (validation_result.missing_pallets or validation_result.quantity_mismatches):
                resolution.status = IssueStatus.RESOLVED
                resolution.mark_resolved(
                    f"✅ Validation completed for PO {po_id}. "
                    f"Total pallets: {po_summary['pallet_count']}, "
                    f"Total quantity: {po_summary['total_quantity']}. "
                    f"{validation_result.validation_summary}"
                )
            else:
                resolution.status = IssueStatus.FAILED
                resolution.resolution_summary = f"Validation failed: {validation_result.validation_summary}"
                
        except Exception as e:
            logger.error(f"Excel validation processing failed: {e}")
            resolution.status = IssueStatus.FAILED
            resolution.resolution_summary = f"Excel validation processing failed: {str(e)}"
    
    async def _handle_generic_workflow(self, resolution: IssueResolution):
        """Handle generic workflow for unspecified actions."""
        try:
            resolution.add_action("Processing generic issue")
            resolution.status = IssueStatus.PROCESSING
            
            # Basic database check
            issue = resolution.classified_issue
            if issue.po_id:
                po_summary = await database_service.get_po_summary(issue.po_id)
                resolution.add_action(f"Retrieved PO summary: {po_summary}")
                
                resolution.status = IssueStatus.RESOLVED
                resolution.mark_resolved(
                    f"✅ Issue processed. PO {issue.po_id} has "
                    f"{po_summary['pallet_count']} pallets with "
                    f"{po_summary['total_quantity']} total quantity."
                )
            else:
                resolution.status = IssueStatus.RESOLVED
                resolution.mark_resolved("✅ Issue acknowledged and logged.")
            
            await self._send_user_notification(resolution)
            
        except Exception as e:
            logger.error(f"Generic workflow failed: {e}")
            resolution.status = IssueStatus.FAILED
            resolution.resolution_summary = f"Generic workflow failed: {str(e)}"
    
    async def _send_user_notification(self, resolution: IssueResolution):
        """Send notification email to user about resolution."""
        try:
            # Generate screenshot if validation results exist
            screenshot_path = None
            if resolution.validation_results:
                po_id = resolution.classified_issue.po_id or "UNKNOWN"
                screenshot_path = await screenshot_service.generate_validation_table_screenshot(
                    resolution.validation_results, po_id
                )
            
            # Send notification
            success = await email_service.send_user_notification(
                user_email=resolution.original_request.user_email,
                issue_id=resolution.issue_id,
                resolution_summary=resolution.resolution_summary,
                screenshot_path=screenshot_path
            )
            
            if success:
                resolution.add_action("User notification sent successfully")
            else:
                resolution.add_action("Failed to send user notification")
                
        except Exception as e:
            logger.error(f"Failed to send user notification: {e}")
            resolution.add_action(f"Failed to send user notification: {str(e)}")
    
    async def get_resolution_status(self, issue_id: str) -> Optional[IssueResolution]:
        """Get the current status of an issue resolution."""
        return self.active_resolutions.get(issue_id)
    
    async def list_active_resolutions(self) -> Dict[str, IssueResolution]:
        """List all active issue resolutions."""
        return self.active_resolutions.copy()
    
    async def cleanup_completed_resolutions(self, max_age_hours: int = 24):
        """Clean up completed resolutions older than specified hours."""
        try:
            current_time = datetime.now()
            completed_ids = []
            
            for issue_id, resolution in self.active_resolutions.items():
                if resolution.status in [IssueStatus.RESOLVED, IssueStatus.FAILED]:
                    if resolution.resolved_at:
                        age = current_time - resolution.resolved_at
                        if age.total_seconds() > (max_age_hours * 3600):
                            completed_ids.append(issue_id)
            
            for issue_id in completed_ids:
                del self.active_resolutions[issue_id]
                logger.info(f"Cleaned up completed resolution: {issue_id}")
                
        except Exception as e:
            logger.error(f"Error during resolution cleanup: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all services."""
        try:
            health_status = {
                "warehouse_agent": "healthy",
                "active_resolutions": len(self.active_resolutions),
                "database": await database_service.health_check(),
                "timestamp": datetime.now().isoformat()
            }
            
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "warehouse_agent": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


# Global warehouse agent instance
warehouse_agent = WarehouseAgent()