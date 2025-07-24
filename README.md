# 🤖 Warehouse AI Agent

An intelligent AI-powered warehouse automation system that resolves issues related to missing ASN, PO, pallets, and quantity mismatches using LLMs, mail automation, PL/SQL triggers, Excel validation, and database integration.

![Python](https://img.shields.io/badge/python-v3.8+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## 🌟 Features

### 🧠 AI-Powered Classification
- **Natural Language Understanding**: Uses LLM technology to automatically understand and classify warehouse issues from user descriptions
- **Multi-Model Support**: Compatible with OpenAI GPT models and free alternatives like Ollama
- **High Accuracy**: Intelligent entity extraction for PO IDs, ASN IDs, and pallet identifiers
- **Confidence Scoring**: Provides confidence levels for classification decisions

### 📧 SAP Integration
- **Automated Email Communication**: Seamless email-based interaction with SAP systems
- **Excel File Processing**: Automatic handling of Excel files received from SAP
- **Response Monitoring**: Intelligent monitoring of SAP email responses with timeout handling
- **Error Recovery**: Robust error handling and retry mechanisms

### 🗄️ Database Management
- **Multi-Database Support**: Compatible with Oracle, PostgreSQL, and MySQL
- **PL/SQL Operations**: Execute complex database procedures for data correction
- **Missing Pallet Insertion**: Automatically insert missing pallets based on SAP data
- **Quantity Corrections**: Update database quantities to match SAP records
- **Audit Trail**: Complete logging of all database operations

### 📊 Visual Reports & Screenshots
- **Validation Screenshots**: Generate visual tables showing validation results
- **Comparison Charts**: Create side-by-side comparisons of SAP vs database data
- **Summary Dashboards**: Comprehensive PO summaries with charts and metrics
- **Email Attachments**: Automatically attach visual reports to user notifications

### 🔄 End-to-End Automation
- **Minimal Human Intervention**: Fully automated workflow from issue submission to resolution
- **Real-time Status Tracking**: Live updates on issue resolution progress
- **Email Notifications**: Automatic user notifications with resolution summaries
- **Background Processing**: Asynchronous processing for optimal performance

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Database (Oracle/PostgreSQL/MySQL)
- Email account for SAP communication
- Optional: Ollama for free local LLM

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/warehouse-ai/warehouse-agent.git
cd warehouse-agent
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Initialize database:**
```bash
# The system will automatically create tables on first run
```

5. **Start the system:**

**Web Server:**
```bash
python -m app.main
# or
python cli.py serve
```

**CLI Interface:**
```bash
python cli.py --help
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with the following configuration:

```env
# AI Configuration
USE_OLLAMA=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2

# Database Configuration
DB_TYPE=postgresql
DB_HOST=localhost
DB_PORT=5432
DB_NAME=warehouse_db
DB_USER=warehouse_user
DB_PASSWORD=your_password

# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=warehouse.agent@company.com
SMTP_PASSWORD=your_app_password

IMAP_SERVER=imap.gmail.com
IMAP_PORT=993
IMAP_USERNAME=warehouse.agent@company.com
IMAP_PASSWORD=your_app_password

# SAP Configuration
SAP_EMAIL=sap.system@company.com
SAP_CC_EMAILS=manager@company.com,supervisor@company.com
```

### Free AI Setup with Ollama

For a completely free setup without OpenAI API:

1. **Install Ollama:**
```bash
# Linux/macOS
curl -fsSL https://ollama.ai/install.sh | sh

# Windows
# Download from https://ollama.ai/download
```

2. **Download a model:**
```bash
ollama pull llama2
# or
ollama pull codellama
ollama pull mistral
```

3. **Configure environment:**
```env
USE_OLLAMA=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
```

## 📖 Usage

### Web Interface

1. **Start the server:**
```bash
python cli.py serve
```

2. **Open browser:** Navigate to `http://localhost:8000`

3. **Submit an issue:** Use the web form to submit warehouse issues like:
   - "PO12345 is missing from the system"
   - "Quantity mismatch for ASN67890"
   - "Pallet PLT001 not found in warehouse"

### CLI Interface

**Submit an issue:**
```bash
python cli.py submit -m "PO12345 is missing" -e "user@company.com"
```

**Check issue status:**
```bash
python cli.py status WH_20241201_143022_abc123
```

**List all issues:**
```bash
python cli.py list --status-filter pending
```

**Classify without processing:**
```bash
python cli.py classify "Quantity mismatch for ASN456"
```

**Get PO information:**
```bash
python cli.py po-info PO12345
```

**System health check:**
```bash
python cli.py health
```

### API Endpoints

**Submit Issue:**
```bash
curl -X POST "http://localhost:8000/api/v1/issues/submit" \
  -H "Content-Type: application/json" \
  -d '{"message": "PO123 is missing", "user_email": "user@company.com"}'
```

**Check Status:**
```bash
curl "http://localhost:8000/api/v1/issues/WH_20241201_143022_abc123/status"
```

**Health Check:**
```bash
curl "http://localhost:8000/api/v1/health"
```

## 🏗️ Architecture

### System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User Input    │    │   AI Classifier │    │   SAP System    │
│                 │    │                 │    │                 │
│ • Web Interface │───▶│ • LLM Analysis  │    │ • Email API     │
│ • CLI           │    │ • Entity Extract│    │ • Excel Export  │
│ • REST API      │    │ • Classification│    │ • Data Trigger  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       ▼                       │
         │            ┌─────────────────┐                │
         │            │ Warehouse Agent │                │
         │            │                 │                │
         │            │ • Orchestration │                │
         │            │ • Workflow Mgmt │                │
         │            │ • Status Track  │                │
         │            └─────────────────┘                │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Database      │    │ Excel Validator │    │ Email Service   │
│                 │    │                 │    │                 │
│ • Oracle/PG/MySQL│   │ • File Processing│   │ • SMTP/IMAP     │
│ • PL/SQL Procs  │    │ • Data Validation│   │ • Monitoring    │
│ • Audit Logs    │    │ • Comparison     │    │ • Notifications │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       ▼                       │
         │            ┌─────────────────┐                │
         │            │Screenshot Service│               │
         │            │                 │                │
         │            │ • Table Images  │                │
         │            │ • Charts/Graphs │                │
         │            │ • Visual Reports│                │
         │            └─────────────────┘                │
         │                                               │
         └───────────────────────────────────────────────┘
```

### Workflow Process

1. **Issue Submission**: User submits issue via web/CLI/API
2. **AI Classification**: LLM analyzes and classifies the issue
3. **Workflow Routing**: System determines appropriate action
4. **SAP Communication**: Automated email to SAP for data
5. **Response Processing**: Handle SAP response and Excel files
6. **Data Validation**: Compare SAP data with database
7. **Database Updates**: Execute PL/SQL procedures for corrections
8. **Visual Reports**: Generate screenshots and comparisons
9. **User Notification**: Send resolution summary with attachments

## 📊 Supported Issue Types

| Issue Type | Description | Action | Requires Excel |
|------------|-------------|--------|----------------|
| **ASN_MISSING** | Missing Advanced Shipping Notice | Send SAP email request | No |
| **PO_MISSING** | Missing Purchase Order | Send SAP email request | No |
| **PALLET_MISSING** | Missing pallets in warehouse | Request Excel validation | Yes |
| **QUANTITY_MISMATCH** | Quantity discrepancies | Request Excel validation | Yes |

## 🔧 Development

### Project Structure

```
warehouse-ai-agent/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── config.py              # Configuration management
│   ├── models.py              # Pydantic data models
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py          # API endpoints
│   └── services/
│       ├── __init__.py
│       ├── ai_classifier.py   # AI classification service
│       ├── email_service.py   # Email handling
│       ├── database_service.py # Database operations
│       ├── excel_validator.py # Excel processing
│       ├── screenshot_service.py # Visual reports
│       └── warehouse_agent.py # Main orchestration
├── cli.py                     # Command-line interface
├── requirements.txt           # Dependencies
├── setup.py                  # Package setup
├── .env.example              # Environment template
└── README.md                 # Documentation
```

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=app
```

### Code Quality

```bash
# Format code
black app/ cli.py

# Sort imports
isort app/ cli.py

# Lint code
flake8 app/ cli.py
```

## 🐳 Docker Deployment

### Docker Compose

```yaml
version: '3.8'
services:
  warehouse-agent:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DB_HOST=postgres
      - DB_NAME=warehouse_db
      - DB_USER=warehouse_user
      - DB_PASSWORD=warehouse_pass
    depends_on:
      - postgres
      - ollama

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: warehouse_db
      POSTGRES_USER: warehouse_user
      POSTGRES_PASSWORD: warehouse_pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

volumes:
  postgres_data:
  ollama_data:
```

### Build and Run

```bash
# Build and start services
docker-compose up -d

# Pull Ollama model
docker-compose exec ollama ollama pull llama2

# Check logs
docker-compose logs -f warehouse-agent
```

## 📈 Monitoring & Logging

### Health Monitoring

- **Health Check Endpoint**: `/api/v1/health`
- **System Statistics**: `/api/v1/stats`
- **Database Status**: Automatic connection health checks
- **Service Monitoring**: Real-time status of all components

### Logging

- **Structured Logging**: JSON-formatted logs with timestamps
- **Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Log Rotation**: Automatic log file rotation
- **Audit Trail**: Complete tracking of all operations

### Metrics

- **Issue Resolution Times**: Track average resolution duration
- **Success Rates**: Monitor resolution success/failure rates
- **Classification Accuracy**: AI model performance metrics
- **System Performance**: Resource usage and response times

## 🔒 Security

### Authentication & Authorization

- **API Keys**: Secure API access with key-based authentication
- **Role-Based Access**: Different permission levels for users
- **Email Security**: Encrypted SMTP/IMAP connections
- **Database Security**: Parameterized queries prevent SQL injection

### Data Protection

- **Sensitive Data**: Automatic masking of sensitive information
- **Audit Logging**: Complete audit trail of all operations
- **Data Retention**: Configurable data retention policies
- **Backup & Recovery**: Database backup and recovery procedures

## 🤝 Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit changes**: `git commit -m 'Add amazing feature'`
4. **Push to branch**: `git push origin feature/amazing-feature`
5. **Open a Pull Request**

### Development Guidelines

- Follow PEP 8 style guidelines
- Write comprehensive tests
- Update documentation
- Use type hints
- Add docstrings to functions

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Documentation

- **API Documentation**: Available at `/docs` when server is running
- **Interactive API**: Test endpoints at `/docs`
- **OpenAPI Spec**: Download from `/openapi.json`

### Getting Help

- **GitHub Issues**: Report bugs and request features
- **Discussions**: Community support and questions
- **Wiki**: Additional documentation and tutorials

### FAQ

**Q: Can I use this without OpenAI API?**
A: Yes! Use Ollama for completely free local LLM processing.

**Q: What databases are supported?**
A: Oracle, PostgreSQL, and MySQL are fully supported.

**Q: How do I customize the AI classification?**
A: Modify the prompts in `app/services/ai_classifier.py` or train custom models.

**Q: Can I integrate with other ERP systems?**
A: Yes, the email service can be adapted for any system that supports email communication.

---

## 🎯 Roadmap

- [ ] **Multi-language Support**: Support for multiple languages in issue descriptions
- [ ] **Advanced Analytics**: Machine learning insights and predictive analytics
- [ ] **Mobile App**: Native mobile application for warehouse staff
- [ ] **Voice Interface**: Voice-activated issue reporting
- [ ] **Integration Hub**: Pre-built connectors for popular ERP systems
- [ ] **Workflow Builder**: Visual workflow designer for custom processes

---

**Built with ❤️ for warehouse automation**

*Powered by AI • Built for Efficiency • Designed for Scale*