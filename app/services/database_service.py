"""Database service for warehouse data management."""

import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import create_engine, text, MetaData, Table, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from loguru import logger

from app.config import settings
from app.models import PalletData, DatabasePallet

Base = declarative_base()


class WarehousePallet(Base):
    """SQLAlchemy model for warehouse pallets."""
    __tablename__ = 'warehouse_pallets'
    
    id = Column(Integer, primary_key=True)
    pallet_id = Column(String(50), unique=True, nullable=False)
    po_id = Column(String(50), nullable=False)
    asn_id = Column(String(50), nullable=True)
    quantity = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default='ACTIVE')
    location = Column(String(100), nullable=True)
    created_date = Column(DateTime, default=datetime.now)
    updated_date = Column(DateTime, nullable=True)


class DatabaseService:
    """Service for database operations."""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize database connection."""
        try:
            self.engine = create_engine(
                settings.database_url,
                pool_pre_ping=True,
                pool_recycle=300,
                echo=settings.debug
            )
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            
            # Create tables if they don't exist
            Base.metadata.create_all(bind=self.engine)
            
            logger.info(f"Database connection initialized: {settings.db_type}")
            
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
            raise
    
    def get_session(self) -> Session:
        """Get database session."""
        return self.SessionLocal()
    
    async def get_pallets_by_po(self, po_id: str) -> List[DatabasePallet]:
        """Get all pallets for a specific PO."""
        try:
            with self.get_session() as session:
                pallets = session.query(WarehousePallet).filter(
                    WarehousePallet.po_id == po_id
                ).all()
                
                return [
                    DatabasePallet(
                        id=p.id,
                        pallet_id=p.pallet_id,
                        po_id=p.po_id,
                        asn_id=p.asn_id,
                        quantity=p.quantity,
                        status=p.status,
                        location=p.location,
                        created_date=p.created_date,
                        updated_date=p.updated_date
                    ) for p in pallets
                ]
                
        except Exception as e:
            logger.error(f"Failed to get pallets for PO {po_id}: {e}")
            return []
    
    async def get_pallet_by_id(self, pallet_id: str) -> Optional[DatabasePallet]:
        """Get specific pallet by ID."""
        try:
            with self.get_session() as session:
                pallet = session.query(WarehousePallet).filter(
                    WarehousePallet.pallet_id == pallet_id
                ).first()
                
                if pallet:
                    return DatabasePallet(
                        id=pallet.id,
                        pallet_id=pallet.pallet_id,
                        po_id=pallet.po_id,
                        asn_id=pallet.asn_id,
                        quantity=pallet.quantity,
                        status=pallet.status,
                        location=pallet.location,
                        created_date=pallet.created_date,
                        updated_date=pallet.updated_date
                    )
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to get pallet {pallet_id}: {e}")
            return None
    
    async def insert_missing_pallets(self, pallets: List[PalletData]) -> bool:
        """Insert missing pallets using PL/SQL procedure."""
        try:
            with self.get_session() as session:
                for pallet in pallets:
                    # Check if pallet already exists
                    existing = session.query(WarehousePallet).filter(
                        WarehousePallet.pallet_id == pallet.pallet_id
                    ).first()
                    
                    if not existing:
                        new_pallet = WarehousePallet(
                            pallet_id=pallet.pallet_id,
                            po_id=pallet.po_id,
                            asn_id=pallet.asn_id,
                            quantity=pallet.quantity,
                            status=pallet.status,
                            location=pallet.location,
                            created_date=datetime.now()
                        )
                        session.add(new_pallet)
                    else:
                        # Update existing pallet
                        existing.quantity = pallet.quantity
                        existing.status = pallet.status
                        existing.location = pallet.location
                        existing.updated_date = datetime.now()
                
                session.commit()
                logger.info(f"Successfully processed {len(pallets)} pallets")
                return True
                
        except Exception as e:
            logger.error(f"Failed to insert missing pallets: {e}")
            return False
    
    async def execute_plsql_procedure(self, procedure_name: str, parameters: Dict[str, Any]) -> bool:
        """Execute PL/SQL procedure with parameters."""
        try:
            with self.get_session() as session:
                # Build procedure call
                param_list = []
                for key, value in parameters.items():
                    if isinstance(value, str):
                        param_list.append(f"'{value}'")
                    else:
                        param_list.append(str(value))
                
                procedure_call = f"CALL {procedure_name}({', '.join(param_list)})"
                
                # Execute procedure
                session.execute(text(procedure_call))
                session.commit()
                
                logger.info(f"PL/SQL procedure {procedure_name} executed successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to execute PL/SQL procedure {procedure_name}: {e}")
            return False
    
    async def update_pallet_quantities(self, quantity_updates: List[Dict[str, Any]]) -> bool:
        """Update pallet quantities in bulk."""
        try:
            with self.get_session() as session:
                for update in quantity_updates:
                    pallet = session.query(WarehousePallet).filter(
                        WarehousePallet.pallet_id == update['pallet_id']
                    ).first()
                    
                    if pallet:
                        pallet.quantity = update['new_quantity']
                        pallet.updated_date = datetime.now()
                
                session.commit()
                logger.info(f"Updated quantities for {len(quantity_updates)} pallets")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update pallet quantities: {e}")
            return False
    
    async def get_po_summary(self, po_id: str) -> Dict[str, Any]:
        """Get summary information for a PO."""
        try:
            with self.get_session() as session:
                # Get pallet count and total quantity
                result = session.execute(text("""
                    SELECT 
                        COUNT(*) as pallet_count,
                        SUM(quantity) as total_quantity,
                        COUNT(DISTINCT asn_id) as asn_count
                    FROM warehouse_pallets 
                    WHERE po_id = :po_id AND status = 'ACTIVE'
                """), {"po_id": po_id}).first()
                
                if result:
                    return {
                        "po_id": po_id,
                        "pallet_count": result.pallet_count or 0,
                        "total_quantity": result.total_quantity or 0,
                        "asn_count": result.asn_count or 0
                    }
                
                return {"po_id": po_id, "pallet_count": 0, "total_quantity": 0, "asn_count": 0}
                
        except Exception as e:
            logger.error(f"Failed to get PO summary for {po_id}: {e}")
            return {"po_id": po_id, "pallet_count": 0, "total_quantity": 0, "asn_count": 0}
    
    async def create_audit_log(self, issue_id: str, action: str, details: Dict[str, Any]) -> bool:
        """Create audit log entry."""
        try:
            with self.get_session() as session:
                # Create audit log table if it doesn't exist
                session.execute(text("""
                    CREATE TABLE IF NOT EXISTS warehouse_audit_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        issue_id VARCHAR(50) NOT NULL,
                        action VARCHAR(100) NOT NULL,
                        details TEXT,
                        created_date DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Insert audit log entry
                session.execute(text("""
                    INSERT INTO warehouse_audit_log (issue_id, action, details)
                    VALUES (:issue_id, :action, :details)
                """), {
                    "issue_id": issue_id,
                    "action": action,
                    "details": str(details)
                })
                
                session.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
            return False
    
    async def get_missing_pallets_for_po(self, po_id: str, expected_pallets: List[str]) -> List[str]:
        """Find missing pallets by comparing expected vs actual."""
        try:
            with self.get_session() as session:
                existing_pallets = session.query(WarehousePallet.pallet_id).filter(
                    WarehousePallet.po_id == po_id,
                    WarehousePallet.status == 'ACTIVE'
                ).all()
                
                existing_ids = {p.pallet_id for p in existing_pallets}
                expected_ids = set(expected_pallets)
                
                missing_pallets = list(expected_ids - existing_ids)
                logger.info(f"Found {len(missing_pallets)} missing pallets for PO {po_id}")
                
                return missing_pallets
                
        except Exception as e:
            logger.error(f"Failed to find missing pallets for PO {po_id}: {e}")
            return []
    
    async def health_check(self) -> bool:
        """Check database connection health."""
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global database service instance
database_service = DatabaseService()