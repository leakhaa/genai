"""
Main Flask application for WMS Automation System
"""
import os
import json
import threading
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from loguru import logger

# Import our modules
from config.settings import get_config
from database.connection import initialize_database, get_session
from database.services import IssueService, WarehouseDataService, PLSQLService, ExcelValidationService, DashboardService
from agents.issue_classifier import IssueClassifier
from email_service.email_sender import EmailService
from excel_validator.validator import ExcelValidator
from screenshot_service.generator import ScreenshotGenerator

# Initialize Flask app
app = Flask(__name__)
config = get_config()
app.config['SECRET_KEY'] = config.SECRET_KEY

# Enable CORS
CORS(app)

# Create upload directory
UPLOAD_FOLDER = config.UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Initialize services
issue_classifier = IssueClassifier()
email_service = EmailService()
excel_validator = ExcelValidator()
screenshot_generator = ScreenshotGenerator()

# Configure logging
logger.add(
    config.LOG_FILE,
    level=config.LOG_LEVEL,
    rotation="10 MB",
    retention="30 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {module}:{function}:{line} - {message}"
)

@app.route('/')
def index():
    """Main dashboard page"""
    try:
        stats = DashboardService.get_issue_statistics()
        return render_template('dashboard.html', stats=stats)
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        return render_template('dashboard.html', stats={})

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    })

@app.route('/api/report-issue', methods=['POST'])
def report_issue():
    """Report a new warehouse issue"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        user_message = data.get('message', '').strip()
        user_email = data.get('user_email', '').strip()
        
        if not user_message:
            return jsonify({"error": "Message is required"}), 400
        
        logger.info(f"New issue reported by {user_email}: {user_message[:100]}...")
        
        # Classify the issue using AI
        classification = issue_classifier.classify_issue(user_message, user_email)
        
        # Generate action plan
        action_plan = issue_classifier.generate_action_plan(classification)
        
        # Create issue in database
        issue_id = IssueService.create_issue(user_message, user_email, classification, action_plan)
        
        # Process the issue in background
        threading.Thread(
            target=process_issue,
            args=(issue_id, classification, action_plan),
            daemon=True
        ).start()
        
        return jsonify({
            "success": True,
            "issue_id": issue_id,
            "classification": classification,
            "action_plan": action_plan,
            "message": "Issue reported and being processed automatically"
        })
        
    except Exception as e:
        logger.error(f"Error reporting issue: {e}")
        return jsonify({"error": "Failed to report issue"}), 500

@app.route('/api/issue-status/<issue_id>')
def get_issue_status(issue_id):
    """Get status of a specific issue"""
    try:
        issue = IssueService.get_issue_by_id(issue_id)
        if not issue:
            return jsonify({"error": "Issue not found"}), 404
        
        return jsonify({
            "success": True,
            "issue": {
                "id": issue.id,
                "status": issue.status.value,
                "priority": issue.priority.value,
                "issue_type": issue.issue_type.value,
                "user_message": issue.user_message,
                "user_email": issue.user_email,
                "created_at": issue.created_at.isoformat(),
                "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
                "resolved_at": issue.resolved_at.isoformat() if issue.resolved_at else None,
                "resolution_notes": issue.resolution_notes
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting issue status: {e}")
        return jsonify({"error": "Failed to get issue status"}), 500

@app.route('/api/validate-excel', methods=['POST'])
def validate_excel():
    """Validate uploaded Excel file"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Save uploaded file
        filename = file.filename
        file_path = os.path.join(config.UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        # Get optional parameters
        po_id = request.form.get('po_id')
        asn_id = request.form.get('asn_id')
        issue_id = request.form.get('issue_id')
        
        # Validate Excel file
        validation_result = excel_validator.validate_excel_file(
            file_path, po_id, asn_id, issue_id
        )
        
        return jsonify({
            "success": True,
            "validation_result": validation_result,
            "message": "Excel file validated successfully"
        })
        
    except Exception as e:
        logger.error(f"Error validating Excel file: {e}")
        return jsonify({"error": "Failed to validate Excel file"}), 500

@app.route('/api/dashboard')
def get_dashboard_data():
    """Get dashboard statistics"""
    try:
        stats = DashboardService.get_issue_statistics()
        return jsonify({
            "success": True,
            "stats": stats
        })
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        return jsonify({"error": "Failed to get dashboard data"}), 500

@app.route('/api/warehouse-data/<data_type>/<entity_id>')
def get_warehouse_data(data_type, entity_id):
    """Get warehouse data (PO, ASN, Pallet)"""
    try:
        data = None
        if data_type == 'po':
            data = WarehouseDataService.get_po_data(entity_id)
        elif data_type == 'asn':
            data = WarehouseDataService.get_asn_data(entity_id)
        elif data_type == 'pallet':
            data = WarehouseDataService.get_pallet_data(entity_id)
        else:
            return jsonify({"error": "Invalid data type"}), 400
        
        if not data:
            return jsonify({"error": f"{data_type.upper()} not found"}), 404
        
        return jsonify({
            "success": True,
            "data": data
        })
        
    except Exception as e:
        logger.error(f"Error getting warehouse data: {e}")
        return jsonify({"error": "Failed to get warehouse data"}), 500

@app.route('/api/user-issues/<user_email>')
def get_user_issues(user_email):
    """Get all issues for a specific user"""
    try:
        issues = IssueService.get_issues_by_user(user_email)
        return jsonify({
            "success": True,
            "issues": [
                {
                    "id": issue.id,
                    "status": issue.status.value,
                    "priority": issue.priority.value,
                    "issue_type": issue.issue_type.value,
                    "user_message": issue.user_message,
                    "created_at": issue.created_at.isoformat(),
                    "resolved_at": issue.resolved_at.isoformat() if issue.resolved_at else None
                }
                for issue in issues
            ]
        })
    except Exception as e:
        logger.error(f"Error getting user issues: {e}")
        return jsonify({"error": "Failed to get user issues"}), 500

def process_issue(issue_id: str, classification: dict, action_plan: dict):
    """Process issue based on classification and action plan"""
    try:
        logger.info(f"Processing issue {issue_id} with type {classification.get('issue_type')}")
        
        # Get action type from action plan
        action_type = action_plan.get('action_type', 'MANUAL_REVIEW')
        
        # Execute appropriate actions
        if action_type == 'EMAIL_SAP_TEAM':
            # Send email to SAP team
            asn_id = classification.get('asn_id')
            po_id = classification.get('po_id')
            
            if classification.get('issue_type') == 'ASN_MISSING':
                result = email_service.send_sap_missing_asn_email(
                    asn_id, classification.get('user_email'), classification
                )
            elif classification.get('issue_type') == 'PO_MISSING':
                result = email_service.send_sap_missing_po_email(
                    po_id, asn_id, classification.get('user_email'), classification
                )
            
            # Log action
            IssueService.log_issue_action(
                issue_id, 'EMAIL_SENT', f"Email sent to SAP team", result
            )
            
        elif action_type == 'EXECUTE_PLSQL':
            # Execute PL/SQL procedure
            procedure_name = action_plan.get('plsql_procedure')
            parameters = action_plan.get('plsql_parameters', [])
            
            result = PLSQLService.execute_procedure(procedure_name, parameters)
            
            # Log action
            IssueService.log_issue_action(
                issue_id, 'PLSQL_EXECUTED', f"Executed {procedure_name}", result
            )
            
        elif action_type == 'VALIDATE_EXCEL':
            # This will be handled when user uploads Excel file
            IssueService.log_issue_action(
                issue_id, 'AWAITING_EXCEL', "Waiting for Excel file upload", {}
            )
            
        elif action_type == 'MANUAL_REVIEW':
            # Send to manual review
            result = email_service.send_manual_review_email(
                issue_id, classification.get('user_email'), classification
            )
            
            IssueService.log_issue_action(
                issue_id, 'MANUAL_REVIEW', "Escalated for manual review", result
            )
        
        # Check if issue is resolved
        if action_plan.get('auto_resolve', False):
            # Generate screenshot
            screenshot_path = screenshot_generator.generate_resolution_screenshot(
                issue_id, classification, action_plan
            )
            
            # Send resolution notification
            email_service.send_resolution_notification(
                classification.get('user_email'),
                issue_id,
                classification,
                action_plan,
                screenshot_path
            )
            
            # Mark issue as resolved
            IssueService.resolve_issue(issue_id, "Automatically resolved", "system")
            
            logger.info(f"Issue {issue_id} resolved automatically")
        
    except Exception as e:
        logger.error(f"Error processing issue {issue_id}: {e}")
        IssueService.log_issue_action(
            issue_id, 'ERROR', f"Processing failed: {str(e)}", {"error": str(e)}
        )

if __name__ == '__main__':
    # Initialize database
    initialize_database()
    
    # Start Flask app
    logger.info("Starting WMS Automation System...")
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=config.DEBUG,
        threaded=True
    )