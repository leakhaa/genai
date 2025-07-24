"""Data models for the Warehouse AI Agent."""

from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator


class IssueType(str, Enum):
    """Types of warehouse issues."""
    ASN_MISSING = "ASN_MISSING"
    PO_MISSING = "PO_MISSING"
    PALLET_MISSING = "PALLET_MISSING"
    QUANTITY_MISMATCH = "QUANTITY_MISMATCH"


class ActionType(str, Enum):
    """Types of actions to be taken."""
    SEND_MAIL_SAP = "SEND_MAIL_SAP"
    REQUEST_EXCEL = "REQUEST_EXCEL"
    VALIDATE_PALLETS = "VALIDATE_PALLETS"
    UPDATE_DATABASE = "UPDATE_DATABASE"
    NOTIFY_USER = "NOTIFY_USER"


class IssueStatus(str, Enum):
    """Status of issue resolution."""
    PENDING = "PENDING"
    EMAIL_SENT = "EMAIL_SENT"
    WAITING_RESPONSE = "WAITING_RESPONSE"
    PROCESSING = "PROCESSING"
    RESOLVED = "RESOLVED"
    FAILED = "FAILED"


class UserIssueRequest(BaseModel):
    """User's issue report."""
    message: str = Field(..., description="User's description of the issue")
    user_email: str = Field(..., description="User's email address")
    timestamp: datetime = Field(default_factory=datetime.now)


class ClassifiedIssue(BaseModel):
    """AI-classified issue structure."""
    issue_type: IssueType
    po_id: Optional[str] = None
    asn_id: Optional[str] = None
    pallet_id: Optional[str] = None
    action: ActionType
    requires_excel: bool = False
    confidence_score: float = Field(ge=0.0, le=1.0)
    extracted_entities: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('confidence_score')
    def validate_confidence(cls, v):
        """Ensure confidence score is between 0 and 1."""
        return max(0.0, min(1.0, v))


class EmailMessage(BaseModel):
    """Email message structure."""
    to: List[str]
    cc: List[str] = Field(default_factory=list)
    subject: str
    body: str
    attachments: List[str] = Field(default_factory=list)
    is_html: bool = False


class SAPResponse(BaseModel):
    """SAP system response."""
    response_type: str  # "confirmation", "excel_data", "error"
    message: str
    excel_file_path: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class PalletData(BaseModel):
    """Pallet information structure."""
    pallet_id: str
    po_id: str
    asn_id: Optional[str] = None
    quantity: int
    expected_quantity: int
    status: str
    location: Optional[str] = None
    created_date: Optional[datetime] = None
    
    @property
    def has_quantity_mismatch(self) -> bool:
        """Check if there's a quantity mismatch."""
        return self.quantity != self.expected_quantity


class ValidationResult(BaseModel):
    """Excel validation result."""
    is_valid: bool
    missing_pallets: List[str] = Field(default_factory=list)
    quantity_mismatches: List[PalletData] = Field(default_factory=list)
    total_pallets_sap: int = 0
    total_pallets_db: int = 0
    validation_summary: str = ""


class IssueResolution(BaseModel):
    """Complete issue resolution tracking."""
    issue_id: str = Field(..., description="Unique issue identifier")
    original_request: UserIssueRequest
    classified_issue: ClassifiedIssue
    status: IssueStatus = IssueStatus.PENDING
    actions_taken: List[str] = Field(default_factory=list)
    sap_responses: List[SAPResponse] = Field(default_factory=list)
    validation_results: Optional[ValidationResult] = None
    resolution_summary: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    
    def add_action(self, action: str) -> None:
        """Add an action to the tracking list."""
        self.actions_taken.append(f"{datetime.now().isoformat()}: {action}")
        self.updated_at = datetime.now()
    
    def mark_resolved(self, summary: str) -> None:
        """Mark the issue as resolved."""
        self.status = IssueStatus.RESOLVED
        self.resolution_summary = summary
        self.resolved_at = datetime.now()
        self.updated_at = datetime.now()


class DatabasePallet(BaseModel):
    """Database pallet record."""
    id: int
    pallet_id: str
    po_id: str
    asn_id: Optional[str]
    quantity: int
    status: str
    location: Optional[str]
    created_date: datetime
    updated_date: Optional[datetime]


class ScreenshotConfig(BaseModel):
    """Configuration for table screenshots."""
    include_screenshot: bool = True
    format: str = "png"  # png, jpg
    dpi: int = 150
    table_style: str = "default"  # default, modern, minimal