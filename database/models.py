"""
Database models for WMS Automation System
"""
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Numeric, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.oracle import RAW
import uuid

Base = declarative_base()

class IssueType(Enum):
    """Enumeration for issue types"""
    ASN_MISSING = "ASN_MISSING"
    PO_MISSING = "PO_MISSING"
    PALLET_MISSING = "PALLET_MISSING"
    QUANTITY_MISMATCH = "QUANTITY_MISMATCH"
    OTHER = "OTHER"

class IssueStatus(Enum):
    """Enumeration for issue status"""
    REPORTED = "REPORTED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"

class Priority(Enum):
    """Enumeration for priority levels"""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class ActionType(Enum):
    """Enumeration for action types"""
    SEND_MAIL_SAP = "SEND_MAIL_SAP"
    TRIGGER_PLSQL = "TRIGGER_PLSQL"
    SEND_MAIL_SAP_AND_VALIDATE_EXCEL = "SEND_MAIL_SAP_AND_VALIDATE_EXCEL"
    MANUAL_REVIEW = "MANUAL_REVIEW"

class Issue(Base):
    """Model for tracking warehouse issues"""
    __tablename__ = 'wms_issues'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    issue_type = Column(SQLEnum(IssueType), nullable=False)
    status = Column(SQLEnum(IssueStatus), default=IssueStatus.REPORTED, nullable=False)
    priority = Column(SQLEnum(Priority), default=Priority.MEDIUM, nullable=False)
    
    # Issue details
    user_message = Column(Text, nullable=False)
    user_email = Column(String(255))
    description = Column(Text)
    
    # Related entities
    asn_id = Column(String(50))
    po_id = Column(String(50))
    pallet_id = Column(String(50))
    
    # Action information
    action_type = Column(SQLEnum(ActionType), nullable=False)
    requires_excel = Column(Boolean, default=False)
    estimated_resolution_hours = Column(Integer, default=4)
    
    # AI classification data
    classification_data = Column(Text)  # JSON string of full classification
    action_plan = Column(Text)  # JSON string of action plan
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime)
    
    # Resolution details
    resolution_notes = Column(Text)
    resolved_by = Column(String(255))
    
    # Relationships
    actions = relationship("IssueAction", back_populates="issue", cascade="all, delete-orphan")
    attachments = relationship("IssueAttachment", back_populates="issue", cascade="all, delete-orphan")

class IssueAction(Base):
    """Model for tracking actions taken on issues"""
    __tablename__ = 'wms_issue_actions'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    issue_id = Column(String(36), ForeignKey('wms_issues.id'), nullable=False)
    
    action_type = Column(String(100), nullable=False)
    action_description = Column(Text)
    action_result = Column(Text)
    
    # Execution details
    executed_at = Column(DateTime, default=datetime.utcnow)
    executed_by = Column(String(255))
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    
    # Email specific fields
    email_sent_to = Column(Text)  # JSON array of email addresses
    email_subject = Column(String(500))
    
    # Database specific fields
    plsql_procedure = Column(String(255))
    plsql_parameters = Column(Text)  # JSON string
    
    # Relationship
    issue = relationship("Issue", back_populates="actions")

class IssueAttachment(Base):
    """Model for issue attachments (Excel files, screenshots, etc.)"""
    __tablename__ = 'wms_issue_attachments'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    issue_id = Column(String(36), ForeignKey('wms_issues.id'), nullable=False)
    
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255))
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    mime_type = Column(String(100))
    
    # File metadata
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    uploaded_by = Column(String(255))
    file_type = Column(String(50))  # 'excel', 'screenshot', 'document'
    
    # Relationship
    issue = relationship("Issue", back_populates="attachments")

class ASN(Base):
    """Model for Advanced Shipping Notice"""
    __tablename__ = 'wms_asn'
    
    asn_id = Column(String(50), primary_key=True)
    asn_number = Column(String(100), unique=True, nullable=False)
    
    # ASN details
    vendor_id = Column(String(50))
    vendor_name = Column(String(255))
    expected_date = Column(DateTime)
    received_date = Column(DateTime)
    
    # Status
    status = Column(String(50), default='EXPECTED')  # EXPECTED, RECEIVED, PROCESSED
    total_pos = Column(Integer, default=0)
    processed_pos = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    purchase_orders = relationship("PurchaseOrder", back_populates="asn")

class PurchaseOrder(Base):
    """Model for Purchase Orders"""
    __tablename__ = 'wms_purchase_orders'
    
    po_id = Column(String(50), primary_key=True)
    po_number = Column(String(100), unique=True, nullable=False)
    asn_id = Column(String(50), ForeignKey('wms_asn.asn_id'))
    
    # PO details
    vendor_id = Column(String(50))
    total_quantity = Column(Numeric(10, 2), default=0)
    received_quantity = Column(Numeric(10, 2), default=0)
    
    # Status
    status = Column(String(50), default='OPEN')  # OPEN, PARTIAL, CLOSED
    total_pallets = Column(Integer, default=0)
    received_pallets = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    asn = relationship("ASN", back_populates="purchase_orders")
    pallets = relationship("Pallet", back_populates="purchase_order")

class Pallet(Base):
    """Model for Pallets"""
    __tablename__ = 'wms_pallets'
    
    pallet_id = Column(String(50), primary_key=True)
    po_id = Column(String(50), ForeignKey('wms_purchase_orders.po_id'))
    
    # Pallet details
    pallet_number = Column(String(100), unique=True, nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False)
    location = Column(String(100))
    
    # Status
    status = Column(String(50), default='EXPECTED')  # EXPECTED, RECEIVED, STORED, SHIPPED
    
    # Physical details
    weight = Column(Numeric(10, 2))
    dimensions = Column(String(100))  # Length x Width x Height
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    received_at = Column(DateTime)
    
    # Relationship
    purchase_order = relationship("PurchaseOrder", back_populates="pallets")

class ExcelValidation(Base):
    """Model for Excel file validation results"""
    __tablename__ = 'wms_excel_validations'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    issue_id = Column(String(36), ForeignKey('wms_issues.id'))
    
    # File details
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500))
    
    # Validation results
    total_records = Column(Integer)
    valid_records = Column(Integer)
    invalid_records = Column(Integer)
    
    # Quantity comparison
    excel_total_quantity = Column(Numeric(12, 2))
    database_total_quantity = Column(Numeric(12, 2))
    quantity_variance = Column(Numeric(12, 2))
    
    # Validation status
    validation_status = Column(String(50))  # PASSED, FAILED, WARNING
    validation_notes = Column(Text)
    validation_errors = Column(Text)  # JSON string of errors
    
    # Timestamps
    validated_at = Column(DateTime, default=datetime.utcnow)
    validated_by = Column(String(255))

class SystemLog(Base):
    """Model for system activity logs"""
    __tablename__ = 'wms_system_logs'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Log details
    log_level = Column(String(20), nullable=False)  # INFO, WARNING, ERROR, DEBUG
    message = Column(Text, nullable=False)
    module = Column(String(100))
    function = Column(String(100))
    
    # Context
    user_id = Column(String(255))
    issue_id = Column(String(36))
    session_id = Column(String(100))
    
    # Additional data
    extra_data = Column(Text)  # JSON string for additional context
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Performance tracking
    execution_time_ms = Column(Integer)
    memory_usage_mb = Column(Numeric(8, 2))