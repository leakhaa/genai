"""Email service for SAP communication and user notifications."""

import os
import email
import smtplib
import imaplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from loguru import logger

from app.config import settings
from app.models import EmailMessage, SAPResponse, IssueType


class EmailService:
    """Service for handling email communication with SAP and users."""
    
    def __init__(self):
        self.smtp_server = None
        self.imap_server = None
    
    async def send_sap_request(self, issue_type: IssueType, po_id: str = None, 
                              asn_id: str = None, pallet_id: str = None) -> bool:
        """Send request email to SAP system."""
        try:
            subject, body = self._build_sap_email_content(issue_type, po_id, asn_id, pallet_id)
            
            email_msg = EmailMessage(
                to=[settings.sap_email],
                cc=settings.sap_cc_emails,
                subject=subject,
                body=body,
                is_html=False
            )
            
            success = await self.send_email(email_msg)
            if success:
                logger.info(f"SAP request sent for {issue_type.value}: PO={po_id}, ASN={asn_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send SAP request: {e}")
            return False
    
    async def send_email(self, email_msg: EmailMessage) -> bool:
        """Send email via SMTP."""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = settings.smtp_username
            msg['To'] = ', '.join(email_msg.to)
            if email_msg.cc:
                msg['Cc'] = ', '.join(email_msg.cc)
            msg['Subject'] = email_msg.subject
            
            # Add body
            if email_msg.is_html:
                msg.attach(MIMEText(email_msg.body, 'html'))
            else:
                msg.attach(MIMEText(email_msg.body, 'plain'))
            
            # Add attachments
            for file_path in email_msg.attachments:
                if os.path.exists(file_path):
                    with open(file_path, "rb") as attachment:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.read())
                    
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {os.path.basename(file_path)}'
                    )
                    msg.attach(part)
            
            # Send email
            with smtplib.SMTP(settings.smtp_server, settings.smtp_port) as server:
                if settings.smtp_use_tls:
                    server.starttls()
                server.login(settings.smtp_username, settings.smtp_password)
                
                recipients = email_msg.to + email_msg.cc
                server.send_message(msg, to_addrs=recipients)
            
            logger.info(f"Email sent successfully to {', '.join(email_msg.to)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    async def monitor_sap_response(self, issue_id: str, timeout_minutes: int = 30) -> Optional[SAPResponse]:
        """Monitor IMAP for SAP response emails."""
        try:
            end_time = datetime.now() + timedelta(minutes=timeout_minutes)
            
            while datetime.now() < end_time:
                response = await self._check_for_sap_response(issue_id)
                if response:
                    return response
                
                # Wait before checking again
                await asyncio.sleep(settings.email_poll_interval)
            
            logger.warning(f"SAP response timeout for issue {issue_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error monitoring SAP response: {e}")
            return None
    
    async def _check_for_sap_response(self, issue_id: str) -> Optional[SAPResponse]:
        """Check IMAP for new SAP response emails."""
        try:
            with imaplib.IMAP4_SSL(settings.imap_server, settings.imap_port) as mail:
                mail.login(settings.imap_username, settings.imap_password)
                mail.select('INBOX')
                
                # Search for emails from SAP in the last hour
                search_date = (datetime.now() - timedelta(hours=1)).strftime("%d-%b-%Y")
                result, message_ids = mail.search(None, f'(FROM "{settings.sap_email}" SINCE "{search_date}")')
                
                if result == 'OK' and message_ids[0]:
                    for msg_id in message_ids[0].split():
                        result, msg_data = mail.fetch(msg_id, '(RFC822)')
                        
                        if result == 'OK':
                            email_body = msg_data[0][1]
                            email_message = email.message_from_bytes(email_body)
                            
                            # Check if this is a response to our request
                            subject = email_message['Subject']
                            if self._is_sap_response(subject, issue_id):
                                return await self._parse_sap_response(email_message)
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking IMAP: {e}")
            return None
    
    async def _parse_sap_response(self, email_message) -> SAPResponse:
        """Parse SAP response email."""
        try:
            subject = email_message['Subject']
            body = self._get_email_body(email_message)
            
            # Check for Excel attachment
            excel_file_path = None
            for part in email_message.walk():
                if part.get_content_disposition() == 'attachment':
                    filename = part.get_filename()
                    if filename and filename.lower().endswith(('.xlsx', '.xls')):
                        # Save attachment
                        os.makedirs(settings.excel_dir, exist_ok=True)
                        excel_file_path = os.path.join(settings.excel_dir, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}")
                        
                        with open(excel_file_path, 'wb') as f:
                            f.write(part.get_payload(decode=True))
                        
                        logger.info(f"Excel file saved: {excel_file_path}")
                        break
            
            # Determine response type
            if excel_file_path:
                response_type = "excel_data"
            elif any(word in body.lower() for word in ['completed', 'processed', 'updated']):
                response_type = "confirmation"
            else:
                response_type = "error"
            
            return SAPResponse(
                response_type=response_type,
                message=body,
                excel_file_path=excel_file_path,
                data={"subject": subject, "sender": email_message['From']}
            )
            
        except Exception as e:
            logger.error(f"Error parsing SAP response: {e}")
            return SAPResponse(
                response_type="error",
                message=f"Failed to parse SAP response: {str(e)}"
            )
    
    async def send_user_notification(self, user_email: str, issue_id: str, 
                                   resolution_summary: str, screenshot_path: str = None) -> bool:
        """Send resolution notification to user."""
        try:
            subject = f"Issue {issue_id} Resolved - Warehouse AI Agent"
            
            body = f"""
Hello,

Your warehouse issue (ID: {issue_id}) has been successfully resolved.

Resolution Summary:
{resolution_summary}

This issue was automatically processed by the Warehouse AI Agent.

Best regards,
Warehouse AI Agent
            """.strip()
            
            attachments = []
            if screenshot_path and os.path.exists(screenshot_path):
                attachments.append(screenshot_path)
            
            email_msg = EmailMessage(
                to=[user_email],
                subject=subject,
                body=body,
                attachments=attachments,
                is_html=False
            )
            
            return await self.send_email(email_msg)
            
        except Exception as e:
            logger.error(f"Failed to send user notification: {e}")
            return False
    
    def _build_sap_email_content(self, issue_type: IssueType, po_id: str = None, 
                               asn_id: str = None, pallet_id: str = None) -> Tuple[str, str]:
        """Build SAP email subject and body."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if issue_type == IssueType.ASN_MISSING:
            subject = f"ASN Missing Request - {asn_id or 'Unknown'}"
            body = f"""
Dear SAP Team,

We have identified a missing ASN in our warehouse management system.

Details:
- Issue Type: ASN Missing
- ASN ID: {asn_id or 'Not specified'}
- PO ID: {po_id or 'Not specified'}
- Timestamp: {timestamp}

Please retrigger the ASN data for the above reference.

This is an automated request from the Warehouse AI Agent.

Best regards,
Warehouse AI Agent
            """.strip()
            
        elif issue_type == IssueType.PO_MISSING:
            subject = f"PO Missing Request - {po_id or 'Unknown'}"
            body = f"""
Dear SAP Team,

We have identified a missing Purchase Order in our warehouse management system.

Details:
- Issue Type: PO Missing
- PO ID: {po_id or 'Not specified'}
- ASN ID: {asn_id or 'Not specified'}
- Timestamp: {timestamp}

Please retrigger the PO data for the above reference.

This is an automated request from the Warehouse AI Agent.

Best regards,
Warehouse AI Agent
            """.strip()
            
        elif issue_type == IssueType.PALLET_MISSING:
            subject = f"Pallet Data Request - {po_id or 'Unknown'}"
            body = f"""
Dear SAP Team,

We need complete pallet data for validation purposes.

Details:
- Issue Type: Pallet Missing/Validation Required
- PO ID: {po_id or 'Not specified'}
- Pallet ID: {pallet_id or 'Not specified'}
- Timestamp: {timestamp}

Please provide the complete PO data in Excel format including all pallet information.

This is an automated request from the Warehouse AI Agent.

Best regards,
Warehouse AI Agent
            """.strip()
            
        else:  # QUANTITY_MISMATCH
            subject = f"Quantity Validation Request - {po_id or 'Unknown'}"
            body = f"""
Dear SAP Team,

We have detected quantity mismatches and need complete data for validation.

Details:
- Issue Type: Quantity Mismatch
- PO ID: {po_id or 'Not specified'}
- ASN ID: {asn_id or 'Not specified'}
- Timestamp: {timestamp}

Please provide the complete PO data in Excel format for validation.

This is an automated request from the Warehouse AI Agent.

Best regards,
Warehouse AI Agent
            """.strip()
        
        return subject, body
    
    def _is_sap_response(self, subject: str, issue_id: str) -> bool:
        """Check if email is a SAP response to our request."""
        subject_lower = subject.lower()
        return any(keyword in subject_lower for keyword in [
            'response', 'reply', 'asn', 'po', 'pallet', 'warehouse', issue_id.lower()
        ])
    
    def _get_email_body(self, email_message) -> str:
        """Extract plain text body from email message."""
        try:
            if email_message.is_multipart():
                for part in email_message.walk():
                    if part.get_content_type() == "text/plain":
                        return part.get_payload(decode=True).decode('utf-8')
            else:
                return email_message.get_payload(decode=True).decode('utf-8')
        except Exception as e:
            logger.error(f"Error extracting email body: {e}")
            return "Could not extract email body"
        
        return "No text content found"


# Global email service instance
email_service = EmailService()