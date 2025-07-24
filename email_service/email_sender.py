"""
Email service for WMS automation system
"""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader
from loguru import logger
from config.settings import get_config

config = get_config()

class EmailService:
    """Service for sending automated emails"""
    
    def __init__(self):
        """Initialize email service with SMTP configuration"""
        self.smtp_server = config.SMTP_SERVER
        self.smtp_port = config.SMTP_PORT
        self.username = config.SMTP_USERNAME
        self.password = config.SMTP_PASSWORD
        self.use_tls = config.SMTP_USE_TLS
        
        # Initialize Jinja2 template environment
        template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        if not os.path.exists(template_dir):
            os.makedirs(template_dir)
        
        self.jinja_env = Environment(loader=FileSystemLoader(template_dir))
    
    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        body: str,
        cc_emails: List[str] = None,
        bcc_emails: List[str] = None,
        attachments: List[str] = None,
        is_html: bool = False
    ) -> Dict[str, Any]:
        """
        Send email with optional attachments
        
        Args:
            to_emails: List of recipient email addresses
            subject: Email subject
            body: Email body content
            cc_emails: List of CC email addresses
            bcc_emails: List of BCC email addresses
            attachments: List of file paths to attach
            is_html: Whether body is HTML content
            
        Returns:
            Dictionary with send result
        """
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = subject
            
            if cc_emails:
                msg['Cc'] = ', '.join(cc_emails)
            
            # Add body
            body_type = 'html' if is_html else 'plain'
            msg.attach(MIMEText(body, body_type))
            
            # Add attachments
            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        self._add_attachment(msg, file_path)
                    else:
                        logger.warning(f"Attachment file not found: {file_path}")
            
            # Prepare recipient list
            all_recipients = to_emails[:]
            if cc_emails:
                all_recipients.extend(cc_emails)
            if bcc_emails:
                all_recipients.extend(bcc_emails)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                
                server.login(self.username, self.password)
                server.send_message(msg, to_addrs=all_recipients)
            
            logger.info(f"Email sent successfully to {len(all_recipients)} recipients")
            
            return {
                'success': True,
                'recipients': all_recipients,
                'subject': subject,
                'message': 'Email sent successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return {
                'success': False,
                'error': str(e),
                'recipients': to_emails,
                'subject': subject
            }
    
    def _add_attachment(self, msg: MIMEMultipart, file_path: str):
        """Add file attachment to email message"""
        try:
            with open(file_path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            
            filename = os.path.basename(file_path)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {filename}'
            )
            
            msg.attach(part)
            logger.debug(f"Added attachment: {filename}")
            
        except Exception as e:
            logger.error(f"Failed to add attachment {file_path}: {e}")
    
    def send_sap_missing_asn_email(
        self,
        asn_id: str,
        user_email: str,
        issue_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send email to SAP team for missing ASN"""
        try:
            template = self.jinja_env.get_template('sap_missing_asn.html')
            
            body = template.render(
                asn_id=asn_id,
                user_email=user_email,
                issue_details=issue_details,
                timestamp=issue_details.get('created_at', 'N/A')
            )
            
            subject = f"[WMS Alert] Missing ASN: {asn_id}"
            
            return self.send_email(
                to_emails=[config.SAP_EMAIL],
                cc_emails=[config.WAREHOUSE_ADMIN_EMAIL, user_email],
                subject=subject,
                body=body,
                is_html=True
            )
            
        except Exception as e:
            logger.error(f"Failed to send SAP missing ASN email: {e}")
            return {'success': False, 'error': str(e)}
    
    def send_sap_missing_po_email(
        self,
        po_id: str,
        asn_id: str,
        user_email: str,
        issue_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send email to SAP team for missing PO"""
        try:
            template = self.jinja_env.get_template('sap_missing_po.html')
            
            body = template.render(
                po_id=po_id,
                asn_id=asn_id,
                user_email=user_email,
                issue_details=issue_details,
                timestamp=issue_details.get('created_at', 'N/A')
            )
            
            subject = f"[WMS Alert] Missing PO: {po_id} (ASN: {asn_id})"
            
            return self.send_email(
                to_emails=[config.SAP_EMAIL],
                cc_emails=[config.WAREHOUSE_ADMIN_EMAIL, user_email],
                subject=subject,
                body=body,
                is_html=True
            )
            
        except Exception as e:
            logger.error(f"Failed to send SAP missing PO email: {e}")
            return {'success': False, 'error': str(e)}
    
    def send_quantity_mismatch_email(
        self,
        po_id: str,
        validation_results: Dict[str, Any],
        user_email: str,
        excel_file_path: str = None
    ) -> Dict[str, Any]:
        """Send email for quantity mismatch with Excel validation"""
        try:
            template = self.jinja_env.get_template('quantity_mismatch.html')
            
            body = template.render(
                po_id=po_id,
                validation_results=validation_results,
                user_email=user_email,
                has_excel=excel_file_path is not None
            )
            
            subject = f"[WMS Alert] Quantity Mismatch: PO {po_id}"
            
            attachments = [excel_file_path] if excel_file_path else None
            
            return self.send_email(
                to_emails=[config.SAP_EMAIL],
                cc_emails=[config.WAREHOUSE_ADMIN_EMAIL, user_email],
                subject=subject,
                body=body,
                attachments=attachments,
                is_html=True
            )
            
        except Exception as e:
            logger.error(f"Failed to send quantity mismatch email: {e}")
            return {'success': False, 'error': str(e)}
    
    def send_resolution_notification(
        self,
        user_email: str,
        issue_id: str,
        issue_details: Dict[str, Any],
        resolution_data: Dict[str, Any],
        screenshot_path: str = None
    ) -> Dict[str, Any]:
        """Send resolution notification to user"""
        try:
            template = self.jinja_env.get_template('resolution_notification.html')
            
            body = template.render(
                issue_id=issue_id,
                issue_details=issue_details,
                resolution_data=resolution_data,
                has_screenshot=screenshot_path is not None
            )
            
            subject = f"[WMS Resolved] Issue {issue_id[:8]} has been resolved"
            
            attachments = [screenshot_path] if screenshot_path else None
            
            return self.send_email(
                to_emails=[user_email],
                cc_emails=[config.WAREHOUSE_ADMIN_EMAIL],
                subject=subject,
                body=body,
                attachments=attachments,
                is_html=True
            )
            
        except Exception as e:
            logger.error(f"Failed to send resolution notification: {e}")
            return {'success': False, 'error': str(e)}
    
    def send_manual_review_notification(
        self,
        issue_id: str,
        issue_details: Dict[str, Any],
        user_email: str
    ) -> Dict[str, Any]:
        """Send notification for issues requiring manual review"""
        try:
            template = self.jinja_env.get_template('manual_review.html')
            
            body = template.render(
                issue_id=issue_id,
                issue_details=issue_details,
                user_email=user_email
            )
            
            subject = f"[WMS Manual Review] Issue {issue_id[:8]} requires manual intervention"
            
            return self.send_email(
                to_emails=[config.WAREHOUSE_ADMIN_EMAIL],
                cc_emails=[user_email],
                subject=subject,
                body=body,
                is_html=True
            )
            
        except Exception as e:
            logger.error(f"Failed to send manual review notification: {e}")
            return {'success': False, 'error': str(e)}
    
    def test_email_connection(self) -> Dict[str, Any]:
        """Test SMTP connection"""
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
            
            logger.info("Email connection test successful")
            return {'success': True, 'message': 'SMTP connection successful'}
            
        except Exception as e:
            logger.error(f"Email connection test failed: {e}")
            return {'success': False, 'error': str(e)}

# Global email service instance
email_service = EmailService()

def send_email(**kwargs):
    """Convenience function to send email"""
    return email_service.send_email(**kwargs)

def send_sap_email(email_type: str, **kwargs):
    """Send SAP-specific emails"""
    if email_type == 'missing_asn':
        return email_service.send_sap_missing_asn_email(**kwargs)
    elif email_type == 'missing_po':
        return email_service.send_sap_missing_po_email(**kwargs)
    elif email_type == 'quantity_mismatch':
        return email_service.send_quantity_mismatch_email(**kwargs)
    else:
        raise ValueError(f"Unknown SAP email type: {email_type}")

def send_user_notification(notification_type: str, **kwargs):
    """Send user notifications"""
    if notification_type == 'resolution':
        return email_service.send_resolution_notification(**kwargs)
    elif notification_type == 'manual_review':
        return email_service.send_manual_review_notification(**kwargs)
    else:
        raise ValueError(f"Unknown notification type: {notification_type}")