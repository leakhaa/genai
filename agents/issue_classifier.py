"""
AI Agent for classifying and parsing warehouse issues using LLM
"""
import json
import openai
from typing import Dict, Any, Optional
from loguru import logger
from config.settings import get_config

config = get_config()

class IssueClassifier:
    """AI-powered issue classifier for warehouse problems"""
    
    def __init__(self):
        """Initialize the classifier with OpenAI API"""
        openai.api_key = config.OPENAI_API_KEY
        self.model = config.AI_MODEL
        self.temperature = config.AI_TEMPERATURE
        self.max_tokens = config.AI_MAX_TOKENS
    
    def classify_issue(self, user_message: str, user_email: str = None) -> Dict[str, Any]:
        """
        Classify a warehouse issue from user message using LLM
        
        Args:
            user_message: The user's description of the warehouse issue
            user_email: Optional user email for context
            
        Returns:
            Dictionary containing classified issue information
        """
        try:
            prompt = self._build_classification_prompt(user_message, user_email)
            
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            result = response.choices[0].message['content'].strip()
            
            # Parse JSON response
            try:
                classification = json.loads(result)
                logger.info(f"Successfully classified issue: {classification}")
                return self._validate_classification(classification)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM JSON response: {e}")
                return self._create_fallback_classification(user_message)
                
        except Exception as e:
            logger.error(f"Error in issue classification: {e}")
            return self._create_fallback_classification(user_message)
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the LLM"""
        return """You are an AI agent specialized in warehouse issue automation for a Warehouse Management System (WMS).

Your role is to analyze user reports about warehouse problems and classify them for automated resolution.

In this warehouse system:
- ASN (Advanced Shipping Notice) contains multiple POs
- PO (Purchase Order) contains multiple pallets  
- Pallet has a quantity value

Common issues reported:
1. ASN Missing - An expected ASN hasn't arrived in the system
2. PO Missing - A PO is missing from an ASN
3. Pallet Missing - A pallet is missing from a PO
4. Quantity Mismatch - Quantities don't match between systems/Excel files

For each issue, determine the appropriate action:
- SEND_MAIL_SAP: Send email to SAP team for system-level issues
- TRIGGER_PLSQL: Execute database procedure for data fixes
- SEND_MAIL_SAP_AND_VALIDATE_EXCEL: Send email and validate with Excel
- MANUAL_REVIEW: Issue requires human intervention

Always respond with valid JSON only, no additional text."""

    def _build_classification_prompt(self, user_message: str, user_email: str = None) -> str:
        """Build the classification prompt for the LLM"""
        prompt = f"""
Classify this warehouse issue report: "{user_message}"

Extract and identify:
1. Type of issue (ASN_MISSING, PO_MISSING, PALLET_MISSING, QUANTITY_MISMATCH, or OTHER)
2. Related IDs (ASN, PO, Pallet numbers if mentioned)
3. Suggested action based on issue type
4. Whether Excel file validation is required
5. Priority level (HIGH, MEDIUM, LOW)
6. Expected resolution timeframe

Output ONLY valid JSON in this exact format:
{{
  "issue_type": "PO_MISSING",
  "asn_id": "ASN456",
  "po_id": "PO123", 
  "pallet_id": "PALT9",
  "action": "SEND_MAIL_SAP",
  "requires_excel": false,
  "priority": "HIGH",
  "estimated_resolution_hours": 2,
  "description": "Brief description of the issue",
  "suggested_recipients": ["sap-team@company.com"]
}}

If specific IDs are not mentioned, use null for those fields.
"""
        
        if user_email:
            prompt += f"\nReporting user email: {user_email}"
            
        return prompt
    
    def _validate_classification(self, classification: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize the classification result"""
        
        # Define valid values
        valid_issue_types = {
            'ASN_MISSING', 'PO_MISSING', 'PALLET_MISSING', 
            'QUANTITY_MISMATCH', 'OTHER'
        }
        valid_actions = {
            'SEND_MAIL_SAP', 'TRIGGER_PLSQL', 
            'SEND_MAIL_SAP_AND_VALIDATE_EXCEL', 'MANUAL_REVIEW'
        }
        valid_priorities = {'HIGH', 'MEDIUM', 'LOW'}
        
        # Validate issue type
        if classification.get('issue_type') not in valid_issue_types:
            classification['issue_type'] = 'OTHER'
        
        # Validate action
        if classification.get('action') not in valid_actions:
            classification['action'] = 'MANUAL_REVIEW'
        
        # Validate priority
        if classification.get('priority') not in valid_priorities:
            classification['priority'] = 'MEDIUM'
        
        # Ensure boolean fields
        classification['requires_excel'] = bool(classification.get('requires_excel', False))
        
        # Ensure numeric fields
        try:
            classification['estimated_resolution_hours'] = int(
                classification.get('estimated_resolution_hours', 4)
            )
        except (ValueError, TypeError):
            classification['estimated_resolution_hours'] = 4
        
        # Add default recipients if not provided
        if not classification.get('suggested_recipients'):
            classification['suggested_recipients'] = [config.SAP_EMAIL]
        
        return classification
    
    def _create_fallback_classification(self, user_message: str) -> Dict[str, Any]:
        """Create a fallback classification when LLM fails"""
        logger.warning("Using fallback classification due to LLM failure")
        
        return {
            "issue_type": "OTHER",
            "asn_id": None,
            "po_id": None,
            "pallet_id": None,
            "action": "MANUAL_REVIEW",
            "requires_excel": False,
            "priority": "MEDIUM",
            "estimated_resolution_hours": 8,
            "description": f"Manual review required for: {user_message[:100]}...",
            "suggested_recipients": [config.WAREHOUSE_ADMIN_EMAIL],
            "fallback_reason": "LLM classification failed"
        }
    
    def generate_action_plan(self, classification: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate detailed action plan based on classification
        
        Args:
            classification: The classified issue information
            
        Returns:
            Dictionary containing detailed action plan
        """
        issue_type = classification['issue_type']
        action = classification['action']
        
        action_plan = {
            'immediate_actions': [],
            'validation_steps': [],
            'notification_steps': [],
            'follow_up_actions': []
        }
        
        # Define actions based on issue type
        if issue_type == 'ASN_MISSING':
            action_plan['immediate_actions'] = [
                'Query database for ASN status',
                'Check EDI logs for transmission issues',
                'Verify ASN in source system'
            ]
            action_plan['notification_steps'] = [
                'Send email to SAP team requesting ASN retrigger',
                'Notify warehouse manager of potential delay'
            ]
            
        elif issue_type == 'PO_MISSING':
            action_plan['immediate_actions'] = [
                'Verify PO exists in source system',
                'Check ASN-PO mapping in database',
                'Execute PO reconciliation procedure'
            ]
            if classification.get('requires_excel'):
                action_plan['validation_steps'] = [
                    'Download Excel file for validation',
                    'Compare PO quantities with database',
                    'Generate discrepancy report'
                ]
                
        elif issue_type == 'PALLET_MISSING':
            action_plan['immediate_actions'] = [
                'Execute pallet search procedure',
                'Check pallet movement history',
                'Verify pallet location in WMS'
            ]
            action_plan['follow_up_actions'] = [
                'Update pallet status if found',
                'Generate new pallet ID if lost',
                'Update inventory counts'
            ]
            
        elif issue_type == 'QUANTITY_MISMATCH':
            action_plan['validation_steps'] = [
                'Download and validate Excel files',
                'Compare quantities across systems',
                'Identify source of discrepancy'
            ]
            action_plan['immediate_actions'] = [
                'Lock affected inventory',
                'Generate quantity variance report',
                'Escalate to inventory control team'
            ]
        
        return action_plan