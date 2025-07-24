"""FastAPI routes for the Warehouse AI Agent."""

from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from loguru import logger

from app.models import UserIssueRequest, IssueResolution
from app.services.warehouse_agent import warehouse_agent

router = APIRouter()


@router.post("/issues/submit", response_model=Dict[str, Any])
async def submit_issue(
    issue_request: UserIssueRequest,
    background_tasks: BackgroundTasks
):
    """Submit a new warehouse issue for processing."""
    try:
        logger.info(f"Received issue submission from {issue_request.user_email}")
        
        # Process the issue in the background
        resolution = await warehouse_agent.process_user_issue(issue_request)
        
        return {
            "success": True,
            "issue_id": resolution.issue_id,
            "status": resolution.status.value,
            "message": "Issue submitted successfully and is being processed",
            "classification": {
                "issue_type": resolution.classified_issue.issue_type.value,
                "action": resolution.classified_issue.action.value,
                "confidence": resolution.classified_issue.confidence_score,
                "extracted_entities": resolution.classified_issue.extracted_entities
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to submit issue: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process issue: {str(e)}")


@router.get("/issues/{issue_id}/status", response_model=Dict[str, Any])
async def get_issue_status(issue_id: str):
    """Get the current status of an issue."""
    try:
        resolution = await warehouse_agent.get_resolution_status(issue_id)
        
        if not resolution:
            raise HTTPException(status_code=404, detail="Issue not found")
        
        return {
            "issue_id": resolution.issue_id,
            "status": resolution.status.value,
            "created_at": resolution.created_at.isoformat(),
            "updated_at": resolution.updated_at.isoformat(),
            "resolved_at": resolution.resolved_at.isoformat() if resolution.resolved_at else None,
            "resolution_summary": resolution.resolution_summary,
            "actions_taken": resolution.actions_taken,
            "classification": {
                "issue_type": resolution.classified_issue.issue_type.value,
                "action": resolution.classified_issue.action.value,
                "po_id": resolution.classified_issue.po_id,
                "asn_id": resolution.classified_issue.asn_id,
                "pallet_id": resolution.classified_issue.pallet_id,
                "confidence": resolution.classified_issue.confidence_score
            },
            "validation_results": resolution.validation_results.dict() if resolution.validation_results else None,
            "sap_responses": [resp.dict() for resp in resolution.sap_responses]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get issue status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get issue status: {str(e)}")


@router.get("/issues", response_model=Dict[str, Any])
async def list_issues(status: str = None, limit: int = 50):
    """List all active issues, optionally filtered by status."""
    try:
        active_resolutions = await warehouse_agent.list_active_resolutions()
        
        # Filter by status if provided
        if status:
            filtered_resolutions = {
                k: v for k, v in active_resolutions.items() 
                if v.status.value.lower() == status.lower()
            }
        else:
            filtered_resolutions = active_resolutions
        
        # Limit results
        limited_resolutions = dict(list(filtered_resolutions.items())[:limit])
        
        # Format response
        issues = []
        for issue_id, resolution in limited_resolutions.items():
            issues.append({
                "issue_id": issue_id,
                "status": resolution.status.value,
                "issue_type": resolution.classified_issue.issue_type.value,
                "created_at": resolution.created_at.isoformat(),
                "updated_at": resolution.updated_at.isoformat(),
                "user_email": resolution.original_request.user_email,
                "message": resolution.original_request.message[:100] + "..." if len(resolution.original_request.message) > 100 else resolution.original_request.message,
                "po_id": resolution.classified_issue.po_id,
                "asn_id": resolution.classified_issue.asn_id
            })
        
        return {
            "total_issues": len(issues),
            "issues": issues,
            "filter_applied": status is not None,
            "status_filter": status
        }
        
    except Exception as e:
        logger.error(f"Failed to list issues: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list issues: {str(e)}")


@router.post("/issues/classify", response_model=Dict[str, Any])
async def classify_issue_only(message: str):
    """Classify an issue without processing it (for testing/preview)."""
    try:
        from app.services.ai_classifier import ai_classifier
        
        classified_issue = await ai_classifier.classify_issue(message)
        
        return {
            "message": message,
            "classification": {
                "issue_type": classified_issue.issue_type.value,
                "action": classified_issue.action.value,
                "po_id": classified_issue.po_id,
                "asn_id": classified_issue.asn_id,
                "pallet_id": classified_issue.pallet_id,
                "requires_excel": classified_issue.requires_excel,
                "confidence_score": classified_issue.confidence_score,
                "extracted_entities": classified_issue.extracted_entities
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to classify issue: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to classify issue: {str(e)}")


@router.get("/health", response_model=Dict[str, Any])
async def health_check():
    """Health check endpoint."""
    try:
        health_status = await warehouse_agent.health_check()
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "warehouse_agent": "unhealthy",
            "error": str(e),
            "timestamp": "unknown"
        }


@router.post("/admin/cleanup", response_model=Dict[str, Any])
async def cleanup_resources(max_age_hours: int = 24):
    """Clean up old resources (admin endpoint)."""
    try:
        # Clean up completed resolutions
        await warehouse_agent.cleanup_completed_resolutions(max_age_hours)
        
        # Clean up temp files
        from app.services.excel_validator import excel_validator
        from app.services.screenshot_service import screenshot_service
        
        excel_validator.cleanup_temp_files(max_age_hours)
        screenshot_service.cleanup_old_screenshots(max_age_hours * 2)  # Keep screenshots longer
        
        return {
            "success": True,
            "message": f"Cleanup completed for resources older than {max_age_hours} hours",
            "timestamp": "now"
        }
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


@router.get("/stats", response_model=Dict[str, Any])
async def get_statistics():
    """Get system statistics."""
    try:
        active_resolutions = await warehouse_agent.list_active_resolutions()
        
        # Calculate statistics
        total_issues = len(active_resolutions)
        status_counts = {}
        issue_type_counts = {}
        
        for resolution in active_resolutions.values():
            # Count by status
            status = resolution.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Count by issue type
            issue_type = resolution.classified_issue.issue_type.value
            issue_type_counts[issue_type] = issue_type_counts.get(issue_type, 0) + 1
        
        return {
            "total_active_issues": total_issues,
            "status_breakdown": status_counts,
            "issue_type_breakdown": issue_type_counts,
            "timestamp": "now"
        }
        
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.post("/test/sap-email", response_model=Dict[str, Any])
async def test_sap_email(issue_type: str, po_id: str = None, asn_id: str = None):
    """Test SAP email functionality (for testing purposes)."""
    try:
        from app.services.email_service import email_service
        from app.models import IssueType
        
        # Convert string to enum
        issue_type_enum = IssueType(issue_type.upper())
        
        success = await email_service.send_sap_request(
            issue_type=issue_type_enum,
            po_id=po_id,
            asn_id=asn_id
        )
        
        return {
            "success": success,
            "message": "SAP email sent successfully" if success else "Failed to send SAP email",
            "issue_type": issue_type,
            "po_id": po_id,
            "asn_id": asn_id
        }
        
    except Exception as e:
        logger.error(f"Failed to test SAP email: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to test SAP email: {str(e)}")


@router.get("/po/{po_id}/summary", response_model=Dict[str, Any])
async def get_po_summary(po_id: str):
    """Get summary information for a specific PO."""
    try:
        from app.services.database_service import database_service
        
        po_summary = await database_service.get_po_summary(po_id)
        pallets = await database_service.get_pallets_by_po(po_id)
        
        return {
            "po_id": po_id,
            "summary": po_summary,
            "pallets": [
                {
                    "pallet_id": p.pallet_id,
                    "quantity": p.quantity,
                    "status": p.status,
                    "location": p.location,
                    "asn_id": p.asn_id,
                    "created_date": p.created_date.isoformat() if p.created_date else None
                }
                for p in pallets
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get PO summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get PO summary: {str(e)}")