"""AI-powered issue classification service."""

import re
import json
import requests
from typing import Dict, Any, Optional
from loguru import logger

from app.config import settings
from app.models import ClassifiedIssue, IssueType, ActionType


class AIClassifier:
    """AI service for classifying warehouse issues."""
    
    def __init__(self):
        self.use_ollama = settings.use_ollama
        if not self.use_ollama and not settings.openai_api_key:
            logger.warning("No AI service configured. Falling back to rule-based classification.")
    
    async def classify_issue(self, user_message: str) -> ClassifiedIssue:
        """Classify user issue using AI or rule-based approach."""
        try:
            if self.use_ollama:
                return await self._classify_with_ollama(user_message)
            elif settings.openai_api_key:
                return await self._classify_with_openai(user_message)
            else:
                return self._classify_with_rules(user_message)
        except Exception as e:
            logger.error(f"AI classification failed: {e}")
            return self._classify_with_rules(user_message)
    
    async def _classify_with_ollama(self, user_message: str) -> ClassifiedIssue:
        """Classify using Ollama (free local LLM)."""
        prompt = self._build_classification_prompt(user_message)
        
        try:
            response = requests.post(
                f"{settings.ollama_base_url}/api/generate",
                json={
                    "model": settings.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            classification_text = result.get("response", "")
            
            return self._parse_classification_response(classification_text, user_message)
            
        except Exception as e:
            logger.error(f"Ollama classification failed: {e}")
            return self._classify_with_rules(user_message)
    
    async def _classify_with_openai(self, user_message: str) -> ClassifiedIssue:
        """Classify using OpenAI API."""
        try:
            import openai
            openai.api_key = settings.openai_api_key
            
            prompt = self._build_classification_prompt(user_message)
            
            response = await openai.ChatCompletion.acreate(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": "You are a warehouse management AI assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            classification_text = response.choices[0].message.content
            return self._parse_classification_response(classification_text, user_message)
            
        except Exception as e:
            logger.error(f"OpenAI classification failed: {e}")
            return self._classify_with_rules(user_message)
    
    def _classify_with_rules(self, user_message: str) -> ClassifiedIssue:
        """Rule-based classification as fallback."""
        message_lower = user_message.lower()
        
        # Extract IDs using regex
        po_match = re.search(r'po[:\s]*([a-zA-Z0-9]+)', message_lower)
        asn_match = re.search(r'asn[:\s]*([a-zA-Z0-9]+)', message_lower)
        pallet_match = re.search(r'pallet[:\s]*([a-zA-Z0-9]+)', message_lower)
        
        po_id = po_match.group(1) if po_match else None
        asn_id = asn_match.group(1) if asn_match else None
        pallet_id = pallet_match.group(1) if pallet_match else None
        
        # Determine issue type based on keywords
        if any(word in message_lower for word in ['missing', 'not found', 'absent']):
            if 'asn' in message_lower:
                issue_type = IssueType.ASN_MISSING
                action = ActionType.SEND_MAIL_SAP
                requires_excel = False
            elif 'po' in message_lower:
                issue_type = IssueType.PO_MISSING
                action = ActionType.SEND_MAIL_SAP
                requires_excel = False
            elif 'pallet' in message_lower:
                issue_type = IssueType.PALLET_MISSING
                action = ActionType.REQUEST_EXCEL
                requires_excel = True
            else:
                issue_type = IssueType.PO_MISSING
                action = ActionType.SEND_MAIL_SAP
                requires_excel = False
        elif any(word in message_lower for word in ['quantity', 'mismatch', 'wrong', 'incorrect']):
            issue_type = IssueType.QUANTITY_MISMATCH
            action = ActionType.VALIDATE_PALLETS
            requires_excel = True
        else:
            # Default to PO missing
            issue_type = IssueType.PO_MISSING
            action = ActionType.SEND_MAIL_SAP
            requires_excel = False
        
        return ClassifiedIssue(
            issue_type=issue_type,
            po_id=po_id,
            asn_id=asn_id,
            pallet_id=pallet_id,
            action=action,
            requires_excel=requires_excel,
            confidence_score=0.7,  # Medium confidence for rule-based
            extracted_entities={
                "po_id": po_id,
                "asn_id": asn_id,
                "pallet_id": pallet_id,
                "keywords": self._extract_keywords(user_message)
            }
        )
    
    def _build_classification_prompt(self, user_message: str) -> str:
        """Build the classification prompt for AI models."""
        return f"""
Analyze the following warehouse issue report and classify it. Return ONLY a JSON response with the following structure:

{{
    "issue_type": "ASN_MISSING|PO_MISSING|PALLET_MISSING|QUANTITY_MISMATCH",
    "po_id": "extracted PO ID or null",
    "asn_id": "extracted ASN ID or null", 
    "pallet_id": "extracted Pallet ID or null",
    "action": "SEND_MAIL_SAP|REQUEST_EXCEL|VALIDATE_PALLETS|UPDATE_DATABASE|NOTIFY_USER",
    "requires_excel": true/false,
    "confidence_score": 0.0-1.0,
    "extracted_entities": {{
        "keywords": ["list", "of", "key", "words"],
        "po_id": "PO123",
        "asn_id": "ASN456"
    }}
}}

Rules:
- ASN_MISSING/PO_MISSING: action = "SEND_MAIL_SAP", requires_excel = false
- PALLET_MISSING: action = "REQUEST_EXCEL", requires_excel = true  
- QUANTITY_MISMATCH: action = "VALIDATE_PALLETS", requires_excel = true

User message: "{user_message}"

JSON Response:"""
    
    def _parse_classification_response(self, response_text: str, original_message: str) -> ClassifiedIssue:
        """Parse AI response into ClassifiedIssue object."""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
                
                return ClassifiedIssue(
                    issue_type=IssueType(data.get("issue_type", "PO_MISSING")),
                    po_id=data.get("po_id"),
                    asn_id=data.get("asn_id"),
                    pallet_id=data.get("pallet_id"),
                    action=ActionType(data.get("action", "SEND_MAIL_SAP")),
                    requires_excel=data.get("requires_excel", False),
                    confidence_score=float(data.get("confidence_score", 0.8)),
                    extracted_entities=data.get("extracted_entities", {})
                )
            else:
                raise ValueError("No JSON found in response")
                
        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")
            return self._classify_with_rules(original_message)
    
    def _extract_keywords(self, text: str) -> list:
        """Extract relevant keywords from text."""
        keywords = []
        text_lower = text.lower()
        
        # Common warehouse keywords
        warehouse_terms = [
            'missing', 'quantity', 'mismatch', 'pallet', 'asn', 'po', 
            'shipment', 'delivery', 'wrong', 'incorrect', 'not found'
        ]
        
        for term in warehouse_terms:
            if term in text_lower:
                keywords.append(term)
        
        # Extract numbers/IDs
        numbers = re.findall(r'\b[A-Z]*\d+[A-Z]*\b', text.upper())
        keywords.extend(numbers[:5])  # Limit to first 5 numbers
        
        return keywords[:10]  # Limit total keywords


# Global classifier instance
ai_classifier = AIClassifier()