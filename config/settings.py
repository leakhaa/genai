"""
Configuration settings for WMS Automation System
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # AI Model Configuration
    AI_MODEL = os.getenv('AI_MODEL', 'gpt-4')
    AI_TEMPERATURE = float(os.getenv('AI_TEMPERATURE', '0.3'))
    AI_MAX_TOKENS = int(os.getenv('AI_MAX_TOKENS', '1000'))
    
    # Database Configuration
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///wms_automation.db')
    
    # Legacy Oracle configuration (for production)
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 1521))
    DB_USER = os.getenv('DB_USER', 'wms_user')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_SERVICE_NAME = os.getenv('DB_SERVICE_NAME', 'ORCL')
    
    # PostgreSQL Configuration
    POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
    POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', 5432))
    POSTGRES_DB = os.getenv('POSTGRES_DB', 'wms_db')
    POSTGRES_USER = os.getenv('POSTGRES_USER', 'postgres')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', '')
    
    # Email Configuration
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
    SMTP_USE_TLS = os.getenv('SMTP_USE_TLS', 'True').lower() == 'true'
    
    # Redis Configuration
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # File Upload Configuration
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 16777216))  # 16MB
    
    # Warehouse Email Configuration
    SAP_TEAM_EMAIL = os.getenv('SAP_TEAM_EMAIL', 'sap-team@company.com')
    WAREHOUSE_MANAGER_EMAIL = os.getenv('WAREHOUSE_MANAGER_EMAIL', 'warehouse-manager@company.com')
    IT_SUPPORT_EMAIL = os.getenv('IT_SUPPORT_EMAIL', 'it-support@company.com')
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/wms_automation.log')

    @property
    def oracle_dsn(self):
        return f"{self.DB_USER}/{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_SERVICE_NAME}"

    @property
    def postgres_url(self):
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

class DevelopmentConfig(Config):
    DEBUG = True
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///wms_automation.db')

class ProductionConfig(Config):
    DEBUG = False
    # Use Oracle or PostgreSQL in production
    DATABASE_URL = os.getenv('DATABASE_URL') or Config().postgres_url

class TestingConfig(Config):
    TESTING = True
    DATABASE_URL = 'sqlite:///:memory:'

def get_config():
    env = os.getenv('FLASK_ENV', 'development')
    if env == 'production':
        return ProductionConfig()
    elif env == 'testing':
        return TestingConfig()
    else:
        return DevelopmentConfig()