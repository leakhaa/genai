"""
Database connection management for WMS Automation System
"""
import cx_Oracle
import psycopg2
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from loguru import logger
from config.settings import get_config
from database.models import Base

config = get_config()

class DatabaseManager:
    """Database connection and session management"""
    
    def __init__(self, use_oracle=True):
        """
        Initialize database manager
        
        Args:
            use_oracle: Whether to use Oracle (True) or PostgreSQL (False)
        """
        self.use_oracle = use_oracle
        self.engine = None
        self.session_factory = None
        self.Session = None
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize database connection and session factory"""
        try:
            if self.use_oracle:
                self._setup_oracle_connection()
            else:
                self._setup_postgres_connection()
            
            # Create session factory
            self.session_factory = sessionmaker(bind=self.engine)
            self.Session = scoped_session(self.session_factory)
            
            logger.info(f"Database connection initialized ({'Oracle' if self.use_oracle else 'PostgreSQL'})")
            
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
            raise
    
    def _setup_oracle_connection(self):
        """Setup Oracle database connection"""
        try:
            # Oracle connection string
            dsn = config.oracle_dsn
            
            # Create engine with connection pooling
            self.engine = create_engine(
                f"oracle+cx_oracle://{dsn}",
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                echo=config.DEBUG
            )
            
            logger.info("Oracle database engine created successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup Oracle connection: {e}")
            raise
    
    def _setup_postgres_connection(self):
        """Setup PostgreSQL database connection"""
        try:
            # PostgreSQL connection URL
            url = config.postgres_url
            
            # Create engine with connection pooling
            self.engine = create_engine(
                url,
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                echo=config.DEBUG
            )
            
            logger.info("PostgreSQL database engine created successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup PostgreSQL connection: {e}")
            raise
    
    def create_tables(self):
        """Create all database tables"""
        try:
            Base.metadata.create_all(self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    def drop_tables(self):
        """Drop all database tables (use with caution!)"""
        try:
            Base.metadata.drop_all(self.engine)
            logger.warning("All database tables dropped")
        except Exception as e:
            logger.error(f"Failed to drop database tables: {e}")
            raise
    
    @contextmanager
    def get_session(self):
        """
        Context manager for database sessions
        
        Usage:
            with db_manager.get_session() as session:
                # Use session here
                pass
        """
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
    
    def execute_raw_sql(self, sql: str, params: dict = None):
        """
        Execute raw SQL query
        
        Args:
            sql: SQL query string
            params: Query parameters
            
        Returns:
            Query results
        """
        try:
            with self.get_session() as session:
                result = session.execute(sql, params or {})
                return result.fetchall()
        except Exception as e:
            logger.error(f"Failed to execute raw SQL: {e}")
            raise
    
    def execute_plsql_procedure(self, procedure_name: str, parameters: list = None):
        """
        Execute PL/SQL stored procedure (Oracle only)
        
        Args:
            procedure_name: Name of the stored procedure
            parameters: List of parameters for the procedure
            
        Returns:
            Procedure execution result
        """
        if not self.use_oracle:
            raise ValueError("PL/SQL procedures are only supported with Oracle database")
        
        try:
            # Get raw Oracle connection
            connection = self.engine.raw_connection()
            cursor = connection.cursor()
            
            try:
                # Execute stored procedure
                cursor.callproc(procedure_name, parameters or [])
                connection.commit()
                
                logger.info(f"Successfully executed PL/SQL procedure: {procedure_name}")
                return {"success": True, "procedure": procedure_name}
                
            except Exception as e:
                connection.rollback()
                logger.error(f"Failed to execute PL/SQL procedure {procedure_name}: {e}")
                raise
            finally:
                cursor.close()
                connection.close()
                
        except Exception as e:
            logger.error(f"Failed to get Oracle connection for PL/SQL: {e}")
            raise
    
    def test_connection(self):
        """Test database connection"""
        try:
            with self.get_session() as session:
                if self.use_oracle:
                    result = session.execute("SELECT 1 FROM DUAL").fetchone()
                else:
                    result = session.execute("SELECT 1").fetchone()
                
                if result:
                    logger.info("Database connection test successful")
                    return True
                else:
                    logger.error("Database connection test failed")
                    return False
                    
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def get_connection_info(self):
        """Get database connection information"""
        try:
            with self.get_session() as session:
                if self.use_oracle:
                    # Oracle version query
                    result = session.execute(
                        "SELECT * FROM V$VERSION WHERE BANNER LIKE 'Oracle%'"
                    ).fetchone()
                    version = result[0] if result else "Unknown"
                    db_type = "Oracle"
                else:
                    # PostgreSQL version query
                    result = session.execute("SELECT version()").fetchone()
                    version = result[0] if result else "Unknown"
                    db_type = "PostgreSQL"
                
                return {
                    "database_type": db_type,
                    "version": version,
                    "host": config.DB_HOST if self.use_oracle else config.POSTGRES_HOST,
                    "connected": True
                }
                
        except Exception as e:
            logger.error(f"Failed to get connection info: {e}")
            return {
                "database_type": "Oracle" if self.use_oracle else "PostgreSQL",
                "version": "Unknown",
                "host": config.DB_HOST if self.use_oracle else config.POSTGRES_HOST,
                "connected": False,
                "error": str(e)
            }

# Global database manager instance
db_manager = None

def initialize_database(use_oracle=True):
    """Initialize global database manager"""
    global db_manager
    db_manager = DatabaseManager(use_oracle=use_oracle)
    return db_manager

def get_db_manager():
    """Get global database manager instance"""
    global db_manager
    if db_manager is None:
        db_manager = initialize_database()
    return db_manager

# Convenience functions
def get_session():
    """Get database session context manager"""
    return get_db_manager().get_session()

def execute_plsql(procedure_name: str, parameters: list = None):
    """Execute PL/SQL procedure"""
    return get_db_manager().execute_plsql_procedure(procedure_name, parameters)

def execute_sql(sql: str, params: dict = None):
    """Execute raw SQL"""
    return get_db_manager().execute_raw_sql(sql, params)