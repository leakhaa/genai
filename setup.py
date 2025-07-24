"""
Setup script for WMS Automation System
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="wms-automation",
    version="1.0.0",
    author="WMS Development Team",
    author_email="dev-team@warehouse.com",
    description="AI-Powered Warehouse Management System Automation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/wms-automation",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Manufacturing",
        "Topic :: Office/Business :: Enterprise",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "black>=23.0",
            "flake8>=6.0",
            "mypy>=1.0",
        ],
        "oracle": [
            "cx-Oracle>=8.3.0",
        ],
        "postgres": [
            "psycopg2-binary>=2.9.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "wms-automation=app:main",
            "wms-test=test_system:main",
        ],
    },
    include_package_data=True,
    package_data={
        "email_service": ["templates/*.html"],
        "static": ["css/*.css", "js/*.js"],
        "templates": ["*.html"],
    },
    zip_safe=False,
)