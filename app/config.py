"""Configuration management for the Warehouse AI Agent."""

import os
from typing import Optional, List
from pydantic import BaseSettings, validator
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings."""
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    
    # Ollama Configuration (free alternative)
    use_ollama: bool = os.getenv("USE_OLLAMA", "false").lower() == "true"
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama2")
    
    # Database Configuration
    db_type: str = os.getenv("DB_TYPE", "oracle")
    db_host: str = os.getenv("DB_HOST", "localhost")
    db_port: int = int(os.getenv("DB_PORT", "1521"))
    db_name: str = os.getenv("DB_NAME", "warehouse_db")
    db_user: str = os.getenv("DB_USER", "warehouse_user")
    db_password: str = os.getenv("DB_PASSWORD", "warehouse_password")
    db_service_name: str = os.getenv("DB_SERVICE_NAME", "XEPDB1")
    
    # Email Configuration
    smtp_server: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str = os.getenv("SMTP_USERNAME", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_use_tls: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    
    imap_server: str = os.getenv("IMAP_SERVER", "imap.gmail.com")
    imap_port: int = int(os.getenv("IMAP_PORT", "993"))
    imap_username: str = os.getenv("IMAP_USERNAME", "")
    imap_password: str = os.getenv("IMAP_PASSWORD", "")
    imap_use_ssl: bool = os.getenv("IMAP_USE_SSL", "true").lower() == "true"
    
    # SAP Configuration
    sap_email: str = os.getenv("SAP_EMAIL", "sap.system@company.com")
    sap_cc_emails: str = os.getenv("SAP_CC_EMAILS", "")
    
    # Application Configuration
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8000"))
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # File Storage
    upload_dir: str = os.getenv("UPLOAD_DIR", "./uploads")
    temp_dir: str = os.getenv("TEMP_DIR", "./temp")
    excel_dir: str = os.getenv("EXCEL_DIR", "./excel_files")
    screenshots_dir: str = os.getenv("SCREENSHOTS_DIR", "./screenshots")
    
    # Polling Configuration
    email_poll_interval: int = int(os.getenv("EMAIL_POLL_INTERVAL", "30"))
    max_retry_attempts: int = int(os.getenv("MAX_RETRY_ATTEMPTS", "5"))
    retry_delay: int = int(os.getenv("RETRY_DELAY", "60"))
    
    @validator('sap_cc_emails')
    def parse_cc_emails(cls, v):
        """Parse comma-separated CC emails."""
        if not v:
            return []
        return [email.strip() for email in v.split(',') if email.strip()]
    
    @property
    def database_url(self) -> str:
        """Generate database URL based on configuration."""
        if self.db_type.lower() == "oracle":
            return f"oracle+cx_oracle://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/?service_name={self.db_service_name}"
        elif self.db_type.lower() == "postgresql":
            return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        elif self.db_type.lower() == "mysql":
            return f"mysql+pymysql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")
    
    class Config:
        env_file = ".env"


# Global settings instance
settings = Settings()