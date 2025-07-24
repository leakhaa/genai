"""
Database connection management for WMS Automation System
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager
from loguru import logger
from config.settings import get_config
from database.models import Base

class DatabaseManager:
    """Database connection and session management"""
    
    def __init__(self, database_url=None):
        """
        Initialize database manager
        
        Args:
            use_oracle: Whether to use Oracle (True) or PostgreSQL (False)
        """
        self.config = get_config()
        self.database_url = database_url or self.config.DATABASE_URL
        self.engine = None
        self.session_factory = None
        self.Session = None
        self.use_oracle = False # Default to False
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize database connection"""
        try:
            # Create engine based on database URL
            if self.database_url.startswith('sqlite'):
                self.engine = create_engine(
                    self.database_url,
                    echo=self.config.DEBUG,
                    connect_args={"check_same_thread": False}  # For SQLite
                )
                self.use_oracle = False
            elif self.database_url.startswith('oracle'):
                self.engine = create_engine(
                    self.database_url,
                    echo=self.config.DEBUG
                )
                self.use_oracle = True
            elif self.database_url.startswith('postgresql'):
                self.engine = create_engine(
                    self.database_url,
                    echo=self.config.DEBUG
                )
                self.use_oracle = False
            else:
                # Fallback to PostgreSQL
                self.engine = create_engine(
                    self.config.postgres_url,
                    echo=self.config.DEBUG
                )
                self.use_oracle = False
            
            self.Session = scoped_session(sessionmaker(bind=self.engine))
            logger.info(f"Database connection initialized: {self.database_url}")
            
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
            raise
    
    def create_tables(self):
        """Create all tables"""
        try:
            Base.metadata.create_all(self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    def drop_tables(self):
        """Drop all tables"""
        try:
            Base.metadata.drop_all(self.engine)
            logger.info("Database tables dropped successfully")
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            raise
    
    @contextmanager
    def get_session(self):
        """Get database session with automatic commit/rollback"""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def execute_raw_sql(self, query: str, parameters: dict = None):
        """Execute raw SQL query"""
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text(query), parameters or {})
                connection.commit()
                return result
        except Exception as e:
            logger.error(f"Failed to execute raw SQL: {e}")
            raise
    
    def execute_plsql_procedure(self, procedure_name: str, parameters: list = None):
        """Execute PL/SQL procedure (Oracle only)"""
        if not self.use_oracle:
            logger.warning("PL/SQL procedures are only supported on Oracle databases")
            return {"status": "skipped", "message": "PL/SQL not supported on this database"}
        
        try:
            with self.engine.connect() as connection:
                # Build procedure call
                param_placeholders = ', '.join([f':param{i}' for i in range(len(parameters or []))])
                query = f"BEGIN {procedure_name}({param_placeholders}); END;"
                
                # Execute procedure
                result = connection.execute(text(query), {f'param{i}': param for i, param in enumerate(parameters or [])})
                connection.commit()
                
                logger.info(f"PL/SQL procedure {procedure_name} executed successfully")
                return {"status": "success", "message": f"Procedure {procedure_name} executed"}
                
        except Exception as e:
            logger.error(f"Failed to execute PL/SQL procedure {procedure_name}: {e}")
            return {"status": "error", "message": str(e)}
    
    def test_connection(self):
        """Test database connection"""
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                logger.info("Database connection test successful")
                return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

# Global database manager instance
db_manager = DatabaseManager()

# Convenience functions
def get_session():
    """Get database session"""
    return db_manager.get_session()

def execute_raw_sql(query: str, parameters: dict = None):
    """Execute raw SQL query"""
    return db_manager.execute_raw_sql(query, parameters)

def execute_plsql(procedure_name: str, parameters: list = None):
    """Execute PL/SQL procedure"""
    return db_manager.execute_plsql_procedure(procedure_name, parameters)

def initialize_database():
    """Initialize database and create tables"""
    db_manager.create_tables()
    return db_manager