"""
Database services for WMS operations
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session
from loguru import logger

from database.connection import get_session, execute_plsql
from database.models import (
    Issue, IssueAction, IssueAttachment, ASN, PurchaseOrder, Pallet,
    ExcelValidation, SystemLog, IssueType, IssueStatus, Priority, ActionType
)

class IssueService:
    """Service for managing warehouse issues"""
    
    @staticmethod
    def create_issue(
        user_message: str,
        user_email: str,
        classification: Dict[str, Any],
        action_plan: Dict[str, Any] = None
    ) -> str:
        """
        Create a new warehouse issue
        
        Args:
            user_message: User's original message
            user_email: User's email address
            classification: AI classification result
            action_plan: Generated action plan
            
        Returns:
            Issue ID
        """
        try:
            with get_session() as session:
                issue = Issue(
                    issue_type=IssueType(classification['issue_type']),
                    user_message=user_message,
                    user_email=user_email,
                    description=classification.get('description'),
                    asn_id=classification.get('asn_id'),
                    po_id=classification.get('po_id'),
                    pallet_id=classification.get('pallet_id'),
                    action_type=ActionType(classification['action']),
                    requires_excel=classification.get('requires_excel', False),
                    estimated_resolution_hours=classification.get('estimated_resolution_hours', 4),
                    priority=Priority(classification.get('priority', 'MEDIUM')),
                    classification_data=json.dumps(classification),
                    action_plan=json.dumps(action_plan) if action_plan else None
                )
                
                session.add(issue)
                session.flush()  # Get the ID
                
                issue_id = issue.id
                logger.info(f"Created issue {issue_id} for user {user_email}")
                
                return issue_id
                
        except Exception as e:
            logger.error(f"Failed to create issue: {e}")
            raise
    
    @staticmethod
    def get_issue(issue_id: str) -> Optional[Issue]:
        """Get issue by ID"""
        try:
            with get_session() as session:
                return session.query(Issue).filter(Issue.id == issue_id).first()
        except Exception as e:
            logger.error(f"Failed to get issue {issue_id}: {e}")
            return None
    
    @staticmethod
    def update_issue_status(
        issue_id: str,
        status: IssueStatus,
        resolution_notes: str = None,
        resolved_by: str = None
    ):
        """Update issue status"""
        try:
            with get_session() as session:
                issue = session.query(Issue).filter(Issue.id == issue_id).first()
                if issue:
                    issue.status = status
                    issue.updated_at = datetime.utcnow()
                    
                    if status == IssueStatus.RESOLVED:
                        issue.resolved_at = datetime.utcnow()
                        issue.resolution_notes = resolution_notes
                        issue.resolved_by = resolved_by
                    
                    logger.info(f"Updated issue {issue_id} status to {status.value}")
                else:
                    logger.warning(f"Issue {issue_id} not found for status update")
                    
        except Exception as e:
            logger.error(f"Failed to update issue status: {e}")
            raise
    
    @staticmethod
    def add_action(
        issue_id: str,
        action_type: str,
        description: str,
        result: str = None,
        success: bool = True,
        executed_by: str = None,
        **kwargs
    ) -> str:
        """Add action to issue"""
        try:
            with get_session() as session:
                action = IssueAction(
                    issue_id=issue_id,
                    action_type=action_type,
                    action_description=description,
                    action_result=result,
                    success=success,
                    executed_by=executed_by,
                    **kwargs
                )
                
                session.add(action)
                session.flush()
                
                action_id = action.id
                logger.info(f"Added action {action_id} to issue {issue_id}")
                
                return action_id
                
        except Exception as e:
            logger.error(f"Failed to add action to issue: {e}")
            raise
    
    @staticmethod
    def get_issues_by_status(status: IssueStatus, limit: int = 100) -> List[Issue]:
        """Get issues by status"""
        try:
            with get_session() as session:
                return session.query(Issue)\
                    .filter(Issue.status == status)\
                    .order_by(Issue.created_at.desc())\
                    .limit(limit)\
                    .all()
        except Exception as e:
            logger.error(f"Failed to get issues by status: {e}")
            return []
    
    @staticmethod
    def get_user_issues(user_email: str, limit: int = 50) -> List[Issue]:
        """Get issues for a specific user"""
        try:
            with get_session() as session:
                return session.query(Issue)\
                    .filter(Issue.user_email == user_email)\
                    .order_by(Issue.created_at.desc())\
                    .limit(limit)\
                    .all()
        except Exception as e:
            logger.error(f"Failed to get user issues: {e}")
            return []

class WarehouseDataService:
    """Service for warehouse data operations"""
    
    @staticmethod
    def get_asn_data(asn_id: str) -> Optional[Dict[str, Any]]:
        """Get ASN data with related POs and pallets"""
        try:
            with get_session() as session:
                asn = session.query(ASN).filter(ASN.asn_id == asn_id).first()
                if not asn:
                    return None
                
                # Get related POs
                pos = session.query(PurchaseOrder)\
                    .filter(PurchaseOrder.asn_id == asn_id)\
                    .all()
                
                # Get total pallets count
                total_pallets = session.query(func.count(Pallet.pallet_id))\
                    .join(PurchaseOrder)\
                    .filter(PurchaseOrder.asn_id == asn_id)\
                    .scalar()
                
                return {
                    'asn_id': asn.asn_id,
                    'asn_number': asn.asn_number,
                    'vendor_name': asn.vendor_name,
                    'status': asn.status,
                    'total_pos': len(pos),
                    'total_pallets': total_pallets,
                    'expected_date': asn.expected_date.isoformat() if asn.expected_date else None,
                    'received_date': asn.received_date.isoformat() if asn.received_date else None,
                    'purchase_orders': [
                        {
                            'po_id': po.po_id,
                            'po_number': po.po_number,
                            'status': po.status,
                            'total_quantity': float(po.total_quantity),
                            'received_quantity': float(po.received_quantity),
                            'total_pallets': po.total_pallets,
                            'received_pallets': po.received_pallets
                        } for po in pos
                    ]
                }
                
        except Exception as e:
            logger.error(f"Failed to get ASN data for {asn_id}: {e}")
            return None
    
    @staticmethod
    def get_po_data(po_id: str) -> Optional[Dict[str, Any]]:
        """Get PO data with related pallets"""
        try:
            with get_session() as session:
                po = session.query(PurchaseOrder).filter(PurchaseOrder.po_id == po_id).first()
                if not po:
                    return None
                
                # Get related pallets
                pallets = session.query(Pallet)\
                    .filter(Pallet.po_id == po_id)\
                    .all()
                
                return {
                    'po_id': po.po_id,
                    'po_number': po.po_number,
                    'asn_id': po.asn_id,
                    'status': po.status,
                    'total_quantity': float(po.total_quantity),
                    'received_quantity': float(po.received_quantity),
                    'total_pallets': po.total_pallets,
                    'received_pallets': po.received_pallets,
                    'pallets': [
                        {
                            'pallet_id': pallet.pallet_id,
                            'pallet_number': pallet.pallet_number,
                            'quantity': float(pallet.quantity),
                            'status': pallet.status,
                            'location': pallet.location,
                            'received_at': pallet.received_at.isoformat() if pallet.received_at else None
                        } for pallet in pallets
                    ]
                }
                
        except Exception as e:
            logger.error(f"Failed to get PO data for {po_id}: {e}")
            return None
    
    @staticmethod
    def get_pallet_data(pallet_id: str) -> Optional[Dict[str, Any]]:
        """Get pallet data"""
        try:
            with get_session() as session:
                pallet = session.query(Pallet).filter(Pallet.pallet_id == pallet_id).first()
                if not pallet:
                    return None
                
                return {
                    'pallet_id': pallet.pallet_id,
                    'pallet_number': pallet.pallet_number,
                    'po_id': pallet.po_id,
                    'quantity': float(pallet.quantity),
                    'status': pallet.status,
                    'location': pallet.location,
                    'weight': float(pallet.weight) if pallet.weight else None,
                    'dimensions': pallet.dimensions,
                    'received_at': pallet.received_at.isoformat() if pallet.received_at else None
                }
                
        except Exception as e:
            logger.error(f"Failed to get pallet data for {pallet_id}: {e}")
            return None
    
    @staticmethod
    def check_missing_entities(classification: Dict[str, Any]) -> Dict[str, bool]:
        """Check if ASN/PO/Pallet actually exist in database"""
        results = {
            'asn_exists': True,
            'po_exists': True,
            'pallet_exists': True
        }
        
        try:
            with get_session() as session:
                # Check ASN
                if classification.get('asn_id'):
                    asn = session.query(ASN).filter(ASN.asn_id == classification['asn_id']).first()
                    results['asn_exists'] = asn is not None
                
                # Check PO
                if classification.get('po_id'):
                    po = session.query(PurchaseOrder).filter(PurchaseOrder.po_id == classification['po_id']).first()
                    results['po_exists'] = po is not None
                
                # Check Pallet
                if classification.get('pallet_id'):
                    pallet = session.query(Pallet).filter(Pallet.pallet_id == classification['pallet_id']).first()
                    results['pallet_exists'] = pallet is not None
                
                return results
                
        except Exception as e:
            logger.error(f"Failed to check missing entities: {e}")
            return results
    
    @staticmethod
    def get_quantity_summary(po_id: str = None, asn_id: str = None) -> Dict[str, Any]:
        """Get quantity summary for PO or ASN"""
        try:
            with get_session() as session:
                if po_id:
                    # Get PO quantity summary
                    po = session.query(PurchaseOrder).filter(PurchaseOrder.po_id == po_id).first()
                    if not po:
                        return None
                    
                    pallets = session.query(Pallet).filter(Pallet.po_id == po_id).all()
                    
                    return {
                        'po_id': po_id,
                        'total_quantity': float(po.total_quantity),
                        'received_quantity': float(po.received_quantity),
                        'pallet_count': len(pallets),
                        'pallet_quantities': [float(p.quantity) for p in pallets],
                        'calculated_total': sum(float(p.quantity) for p in pallets)
                    }
                
                elif asn_id:
                    # Get ASN quantity summary
                    pos = session.query(PurchaseOrder).filter(PurchaseOrder.asn_id == asn_id).all()
                    
                    total_quantity = sum(float(po.total_quantity) for po in pos)
                    received_quantity = sum(float(po.received_quantity) for po in pos)
                    
                    all_pallets = []
                    for po in pos:
                        pallets = session.query(Pallet).filter(Pallet.po_id == po.po_id).all()
                        all_pallets.extend(pallets)
                    
                    return {
                        'asn_id': asn_id,
                        'total_quantity': total_quantity,
                        'received_quantity': received_quantity,
                        'po_count': len(pos),
                        'pallet_count': len(all_pallets),
                        'calculated_total': sum(float(p.quantity) for p in all_pallets)
                    }
                
        except Exception as e:
            logger.error(f"Failed to get quantity summary: {e}")
            return None

class PLSQLService:
    """Service for executing PL/SQL procedures"""
    
    @staticmethod
    def trigger_missing_asn(asn_id: str) -> Dict[str, Any]:
        """Trigger missing ASN procedure"""
        try:
            result = execute_plsql('WMS_MISSING_ASN_PROC', [asn_id])
            logger.info(f"Executed missing ASN procedure for {asn_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to execute missing ASN procedure: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def trigger_missing_po(po_id: str, asn_id: str = None) -> Dict[str, Any]:
        """Trigger missing PO procedure"""
        try:
            params = [po_id]
            if asn_id:
                params.append(asn_id)
            
            result = execute_plsql('WMS_MISSING_PO_PROC', params)
            logger.info(f"Executed missing PO procedure for {po_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to execute missing PO procedure: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def trigger_missing_pallet(pallet_id: str, po_id: str) -> Dict[str, Any]:
        """Trigger missing pallet procedure"""
        try:
            result = execute_plsql('WMS_MISSING_PALLET_PROC', [pallet_id, po_id])
            logger.info(f"Executed missing pallet procedure for {pallet_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to execute missing pallet procedure: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def reconcile_quantities(po_id: str) -> Dict[str, Any]:
        """Reconcile quantity discrepancies"""
        try:
            result = execute_plsql('WMS_QUANTITY_RECONCILE_PROC', [po_id])
            logger.info(f"Executed quantity reconciliation for {po_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to execute quantity reconciliation: {e}")
            return {"success": False, "error": str(e)}

class ExcelValidationService:
    """Service for Excel validation operations"""
    
    @staticmethod
    def save_validation_result(
        issue_id: str,
        filename: str,
        validation_result: Dict[str, Any]
    ) -> str:
        """Save Excel validation result"""
        try:
            with get_session() as session:
                validation = ExcelValidation(
                    issue_id=issue_id,
                    filename=filename,
                    total_records=validation_result.get('total_records', 0),
                    valid_records=validation_result.get('valid_records', 0),
                    invalid_records=validation_result.get('invalid_records', 0),
                    excel_total_quantity=validation_result.get('excel_total', 0),
                    database_total_quantity=validation_result.get('database_total', 0),
                    quantity_variance=validation_result.get('variance', 0),
                    validation_status=validation_result.get('status', 'UNKNOWN'),
                    validation_notes=validation_result.get('notes'),
                    validation_errors=json.dumps(validation_result.get('errors', [])),
                    validated_by=validation_result.get('validated_by')
                )
                
                session.add(validation)
                session.flush()
                
                validation_id = validation.id
                logger.info(f"Saved Excel validation result {validation_id}")
                
                return validation_id
                
        except Exception as e:
            logger.error(f"Failed to save validation result: {e}")
            raise

class DashboardService:
    """Service for dashboard and reporting"""
    
    @staticmethod
    def get_issue_statistics(days: int = 30) -> Dict[str, Any]:
        """Get issue statistics for dashboard"""
        try:
            with get_session() as session:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                
                # Total issues
                total_issues = session.query(func.count(Issue.id))\
                    .filter(Issue.created_at >= cutoff_date)\
                    .scalar()
                
                # Issues by status
                status_counts = session.query(Issue.status, func.count(Issue.id))\
                    .filter(Issue.created_at >= cutoff_date)\
                    .group_by(Issue.status)\
                    .all()
                
                # Issues by type
                type_counts = session.query(Issue.issue_type, func.count(Issue.id))\
                    .filter(Issue.created_at >= cutoff_date)\
                    .group_by(Issue.issue_type)\
                    .all()
                
                # Average resolution time
                avg_resolution = session.query(
                    func.avg(
                        func.extract('epoch', Issue.resolved_at - Issue.created_at) / 3600
                    )
                ).filter(
                    and_(
                        Issue.created_at >= cutoff_date,
                        Issue.status == IssueStatus.RESOLVED
                    )
                ).scalar()
                
                return {
                    'total_issues': total_issues,
                    'status_distribution': {status.value: count for status, count in status_counts},
                    'type_distribution': {issue_type.value: count for issue_type, count in type_counts},
                    'average_resolution_hours': float(avg_resolution) if avg_resolution else 0,
                    'period_days': days
                }
                
        except Exception as e:
            logger.error(f"Failed to get issue statistics: {e}")
            return {}