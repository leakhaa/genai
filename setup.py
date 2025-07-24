"""Setup script for Warehouse AI Agent."""

from setuptools import setup, find_packages

setup(
    name="warehouse-ai-agent",
    version="1.0.0",
    description="Intelligent AI-powered warehouse automation system",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Warehouse AI Team",
    author_email="admin@warehouse-ai.com",
    url="https://github.com/warehouse-ai/warehouse-agent",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        # Core dependencies
        "fastapi==0.104.1",
        "uvicorn==0.24.0",
        "pydantic==2.5.0",
        "python-dotenv==1.0.0",
        
        # AI/ML dependencies
        "openai==1.3.7",
        "transformers==4.36.0",
        "torch==2.1.0",
        "sentence-transformers==2.2.2",
        
        # Database dependencies
        "sqlalchemy==2.0.23",
        "cx-oracle==8.3.0",
        "psycopg2-binary==2.9.9",
        "pymysql==1.1.0",
        
        # Email dependencies
        "imaplib2==3.6",
        "smtplib2==0.2.0",
        "email-validator==2.1.0",
        
        # Excel/Data processing
        "pandas==2.1.3",
        "openpyxl==3.1.2",
        "xlrd==2.0.1",
        
        # Web scraping and automation
        "requests==2.31.0",
        "beautifulsoup4==4.12.2",
        
        # Image processing for screenshots
        "pillow==10.1.0",
        "matplotlib==3.8.2",
        "dataframe-image==0.2.0",
        
        # Utilities
        "python-multipart==0.0.6",
        "jinja2==3.1.2",
        "aiofiles==23.2.0",
        "schedule==1.2.0",
        "python-dateutil==2.8.2",
        "pytz==2023.3",
        
        # Logging and monitoring
        "loguru==0.7.2",
        
        # CLI
        "click==8.1.7",
    ],
    extras_require={
        "dev": [
            "pytest==7.4.3",
            "pytest-asyncio==0.21.1",
            "httpx==0.25.2",
            "black==23.11.0",
            "isort==5.12.0",
            "flake8==6.1.0",
        ],
        "oracle": [
            "cx-oracle==8.3.0",
        ],
        "postgresql": [
            "psycopg2-binary==2.9.9",
        ],
        "mysql": [
            "pymysql==1.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "warehouse-agent=cli:cli",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Office/Business :: Financial :: Point-Of-Sale",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    keywords="warehouse automation ai llm sap excel database",
)