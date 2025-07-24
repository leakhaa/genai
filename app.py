"""
Main Flask application for WMS Automation System
"""
import os
import json
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from loguru import logger

# Import our services
from config.settings import get_config
from database.connection import initialize_database, get_db_manager
from database.services import IssueService, WarehouseDataService, DashboardService
from agents.issue_classifier import IssueClassifier
from email_service.email_sender import email_service
from excel_validator.validator import excel_validator
from screenshot_service.generator import screenshot_generator

# Initialize configuration
config = get_config()

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH

# Enable CORS
CORS(app)

# Create upload directory
UPLOAD_FOLDER = config.UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Initialize services
issue_classifier = IssueClassifier()
issue_service = IssueService()
warehouse_service = WarehouseDataService()
dashboard_service = DashboardService()

# Initialize database
try:
    db_manager = initialize_database(use_oracle=True)  # Change to False for PostgreSQL
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")
    db_manager = None

@app.route('/')
def index():
    """Main dashboard page"""
    try:
        # Get dashboard statistics
        stats = dashboard_service.get_issue_statistics()
        return render_template('dashboard.html', stats=stats)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return render_template('dashboard.html', stats={}, error=str(e))

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db_connected = db_manager.test_connection() if db_manager else False
        
        # Test email connection
        email_result = email_service.test_email_connection()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'services': {
                'database': 'connected' if db_connected else 'disconnected',
                'email': 'connected' if email_result['success'] else 'disconnected',
                'ai_classifier': 'available',
                'excel_validator': 'available',
                'screenshot_generator': 'available'
            }
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.route('/api/report-issue', methods=['POST'])
def report_issue():
    """Report a warehouse issue"""
    try:
        data = request.get_json()
        
        # Validate input
        if not data or 'message' not in data:
            return jsonify({'error': 'Message is required'}), 400
        
        user_message = data['message']
        user_email = data.get('user_email', 'anonymous@warehouse.com')
        
        logger.info(f"Received issue report from {user_email}: {user_message}")
        
        # Classify the issue using AI
        classification = issue_classifier.classify_issue(user_message, user_email)
        
        # Generate action plan
        action_plan = issue_classifier.generate_action_plan(classification)
        
        # Create issue in database
        issue_id = issue_service.create_issue(
            user_message=user_message,
            user_email=user_email,
            classification=classification,
            action_plan=action_plan
        )
        
        # Process the issue based on classification
        processing_result = process_issue(issue_id, classification, action_plan)
        
        return jsonify({
            'success': True,
            'issue_id': issue_id,
            'classification': classification,
            'action_plan': action_plan,
            'processing_result': processing_result,
            'message': f'Issue {issue_id[:8]} has been created and is being processed'
        })
        
    except Exception as e:
        logger.error(f"Failed to report issue: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/issue-status/<issue_id>', methods=['GET'])
def get_issue_status(issue_id):
    """Get issue status and details"""
    try:
        issue = issue_service.get_issue(issue_id)
        
        if not issue:
            return jsonify({'error': 'Issue not found'}), 404
        
        # Convert issue to dictionary
        issue_data = {
            'id': issue.id,
            'issue_type': issue.issue_type.value,
            'status': issue.status.value,
            'priority': issue.priority.value,
            'user_message': issue.user_message,
            'user_email': issue.user_email,
            'description': issue.description,
            'asn_id': issue.asn_id,
            'po_id': issue.po_id,
            'pallet_id': issue.pallet_id,
            'action_type': issue.action_type.value,
            'requires_excel': issue.requires_excel,
            'estimated_resolution_hours': issue.estimated_resolution_hours,
            'created_at': issue.created_at.isoformat(),
            'updated_at': issue.updated_at.isoformat(),
            'resolved_at': issue.resolved_at.isoformat() if issue.resolved_at else None,
            'resolution_notes': issue.resolution_notes,
            'resolved_by': issue.resolved_by
        }
        
        # Get related actions
        actions = [
            {
                'id': action.id,
                'action_type': action.action_type,
                'description': action.action_description,
                'result': action.action_result,
                'success': action.success,
                'executed_at': action.executed_at.isoformat(),
                'executed_by': action.executed_by
            }
            for action in issue.actions
        ]
        
        return jsonify({
            'issue': issue_data,
            'actions': actions
        })
        
    except Exception as e:
        logger.error(f"Failed to get issue status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/validate-excel', methods=['POST'])
def validate_excel():
    """Upload and validate Excel file"""
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Get additional parameters
        po_id = request.form.get('po_id')
        asn_id = request.form.get('asn_id')
        issue_id = request.form.get('issue_id')
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        logger.info(f"Uploaded Excel file: {filepath}")
        
        # Validate the Excel file
        validation_result = excel_validator.validate_excel_file(
            file_path=filepath,
            po_id=po_id,
            asn_id=asn_id,
            issue_id=issue_id
        )
        
        # Generate validation report
        report = excel_validator.generate_validation_report(validation_result)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'validation_result': validation_result,
            'report': report
        })
        
    except Exception as e:
        logger.error(f"Excel validation failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard_data():
    """Get dashboard statistics"""
    try:
        days = request.args.get('days', 30, type=int)
        stats = dashboard_service.get_issue_statistics(days=days)
        
        return jsonify({
            'success': True,
            'statistics': stats
        })
        
    except Exception as e:
        logger.error(f"Failed to get dashboard data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/warehouse-data/<data_type>/<entity_id>', methods=['GET'])
def get_warehouse_data(data_type, entity_id):
    """Get warehouse data (ASN, PO, or Pallet)"""
    try:
        if data_type == 'asn':
            data = warehouse_service.get_asn_data(entity_id)
        elif data_type == 'po':
            data = warehouse_service.get_po_data(entity_id)
        elif data_type == 'pallet':
            data = warehouse_service.get_pallet_data(entity_id)
        else:
            return jsonify({'error': 'Invalid data type'}), 400
        
        if not data:
            return jsonify({'error': f'{data_type.upper()} {entity_id} not found'}), 404
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        logger.error(f"Failed to get warehouse data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/user-issues/<user_email>', methods=['GET'])
def get_user_issues(user_email):
    """Get issues for a specific user"""
    try:
        limit = request.args.get('limit', 50, type=int)
        issues = issue_service.get_user_issues(user_email, limit=limit)
        
        issues_data = [
            {
                'id': issue.id,
                'issue_type': issue.issue_type.value,
                'status': issue.status.value,
                'priority': issue.priority.value,
                'description': issue.description,
                'created_at': issue.created_at.isoformat(),
                'resolved_at': issue.resolved_at.isoformat() if issue.resolved_at else None
            }
            for issue in issues
        ]
        
        return jsonify({
            'success': True,
            'issues': issues_data,
            'count': len(issues_data)
        })
        
    except Exception as e:
        logger.error(f"Failed to get user issues: {e}")
        return jsonify({'error': str(e)}), 500

def process_issue(issue_id: str, classification: dict, action_plan: dict):
    """Process an issue based on its classification"""
    try:
        issue_type = classification['issue_type']
        action = classification['action']
        
        logger.info(f"Processing issue {issue_id} - Type: {issue_type}, Action: {action}")
        
        # Update issue status to IN_PROGRESS
        from database.models import IssueStatus
        issue_service.update_issue_status(issue_id, IssueStatus.IN_PROGRESS)
        
        processing_results = []
        
        if action == 'SEND_MAIL_SAP':
            result = handle_sap_email(issue_id, classification)
            processing_results.append(result)
            
        elif action == 'TRIGGER_PLSQL':
            result = handle_plsql_execution(issue_id, classification)
            processing_results.append(result)
            
        elif action == 'SEND_MAIL_SAP_AND_VALIDATE_EXCEL':
            # Send email first
            email_result = handle_sap_email(issue_id, classification)
            processing_results.append(email_result)
            
            # Note: Excel validation will be handled when file is uploaded
            
        elif action == 'MANUAL_REVIEW':
            result = handle_manual_review(issue_id, classification)
            processing_results.append(result)
        
        # Check if issue can be automatically resolved
        if all(result.get('success', False) for result in processing_results):
            # Generate resolution screenshot
            issue = issue_service.get_issue(issue_id)
            if issue:
                issue_data = {
                    'issue_type': issue.issue_type.value,
                    'user_message': issue.user_message,
                    'asn_id': issue.asn_id,
                    'po_id': issue.po_id,
                    'pallet_id': issue.pallet_id
                }
                
                resolution_data = {
                    'status': 'RESOLVED',
                    'resolved_at': datetime.utcnow().isoformat(),
                    'action': 'Automated resolution completed',
                    'notes': 'Issue has been automatically resolved through system processing.'
                }
                
                screenshot_path = screenshot_generator.generate_resolution_screenshot(
                    issue_id, issue_data, resolution_data
                )
                
                # Send resolution notification
                if issue.user_email:
                    email_service.send_resolution_notification(
                        user_email=issue.user_email,
                        issue_id=issue_id,
                        issue_details=issue_data,
                        resolution_data=resolution_data,
                        screenshot_path=screenshot_path
                    )
                
                # Update issue status to RESOLVED
                issue_service.update_issue_status(
                    issue_id, 
                    IssueStatus.RESOLVED,
                    resolution_notes='Automatically resolved through system processing',
                    resolved_by='WMS Automation System'
                )
        
        return {
            'success': True,
            'results': processing_results
        }
        
    except Exception as e:
        logger.error(f"Failed to process issue {issue_id}: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def handle_sap_email(issue_id: str, classification: dict):
    """Handle sending email to SAP team"""
    try:
        issue_type = classification['issue_type']
        
        # Get issue details
        issue = issue_service.get_issue(issue_id)
        if not issue:
            return {'success': False, 'error': 'Issue not found'}
        
        issue_details = {
            'created_at': issue.created_at.isoformat(),
            'priority': issue.priority.value,
            'description': issue.description or issue.user_message
        }
        
        if issue_type == 'ASN_MISSING':
            result = email_service.send_sap_missing_asn_email(
                asn_id=classification.get('asn_id'),
                user_email=issue.user_email,
                issue_details=issue_details
            )
        elif issue_type == 'PO_MISSING':
            result = email_service.send_sap_missing_po_email(
                po_id=classification.get('po_id'),
                asn_id=classification.get('asn_id'),
                user_email=issue.user_email,
                issue_details=issue_details
            )
        elif issue_type == 'QUANTITY_MISMATCH':
            result = email_service.send_quantity_mismatch_email(
                po_id=classification.get('po_id'),
                validation_results={},  # Will be filled when Excel is validated
                user_email=issue.user_email
            )
        else:
            return {'success': False, 'error': 'Unknown issue type for SAP email'}
        
        # Log the action
        issue_service.add_action(
            issue_id=issue_id,
            action_type='EMAIL_SENT',
            description=f'Sent {issue_type} email to SAP team',
            result=json.dumps(result),
            success=result['success'],
            executed_by='WMS Automation System'
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to send SAP email: {e}")
        return {'success': False, 'error': str(e)}

def handle_plsql_execution(issue_id: str, classification: dict):
    """Handle PL/SQL procedure execution"""
    try:
        from database.services import PLSQLService
        
        issue_type = classification['issue_type']
        plsql_service = PLSQLService()
        
        if issue_type == 'ASN_MISSING':
            result = plsql_service.trigger_missing_asn(classification.get('asn_id'))
        elif issue_type == 'PO_MISSING':
            result = plsql_service.trigger_missing_po(
                classification.get('po_id'),
                classification.get('asn_id')
            )
        elif issue_type == 'PALLET_MISSING':
            result = plsql_service.trigger_missing_pallet(
                classification.get('pallet_id'),
                classification.get('po_id')
            )
        elif issue_type == 'QUANTITY_MISMATCH':
            result = plsql_service.reconcile_quantities(classification.get('po_id'))
        else:
            return {'success': False, 'error': 'Unknown issue type for PL/SQL execution'}
        
        # Log the action
        issue_service.add_action(
            issue_id=issue_id,
            action_type='PLSQL_EXECUTED',
            description=f'Executed PL/SQL procedure for {issue_type}',
            result=json.dumps(result),
            success=result['success'],
            executed_by='WMS Automation System'
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to execute PL/SQL: {e}")
        return {'success': False, 'error': str(e)}

def handle_manual_review(issue_id: str, classification: dict):
    """Handle manual review notification"""
    try:
        issue = issue_service.get_issue(issue_id)
        if not issue:
            return {'success': False, 'error': 'Issue not found'}
        
        issue_details = {
            'issue_type': issue.issue_type.value,
            'user_message': issue.user_message,
            'priority': issue.priority.value,
            'created_at': issue.created_at.isoformat()
        }
        
        result = email_service.send_manual_review_notification(
            issue_id=issue_id,
            issue_details=issue_details,
            user_email=issue.user_email
        )
        
        # Log the action
        issue_service.add_action(
            issue_id=issue_id,
            action_type='MANUAL_REVIEW_REQUESTED',
            description='Sent manual review notification to warehouse admin',
            result=json.dumps(result),
            success=result['success'],
            executed_by='WMS Automation System'
        )
        
        # Update issue status to ESCALATED
        from database.models import IssueStatus
        issue_service.update_issue_status(issue_id, IssueStatus.ESCALATED)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to handle manual review: {e}")
        return {'success': False, 'error': str(e)}

if __name__ == '__main__':
    # Setup logging
    logger.add(
        config.LOG_FILE,
        rotation="10 MB",
        retention="30 days",
        level=config.LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
    )
    
    logger.info("Starting WMS Automation System")
    
    # Create database tables if they don't exist
    if db_manager:
        try:
            db_manager.create_tables()
            logger.info("Database tables created/verified")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
    
    # Start the Flask application
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=config.DEBUG
    )