# AI-Powered Warehouse Management System (WMS) Automation

🔧 **Smart Agent System for Missing PO/ASN/Pallet Resolution**

This system combines LLMs, rule-based logic, email automation, database access, and data validation to automatically resolve warehouse issues.

## Problem Solved

In warehouse operations:
- **ASN** → contains multiple POs
- **PO** → contains multiple pallets  
- **Pallet** → has a quantity value

Users report missing:
- ASN
- PO
- Pallet
- Quantity mismatches

## System Capabilities

1. **AI Issue Analysis** - LLM categorizes and parses user reports
2. **Automated Actions** - Triggers emails or scripts based on issue type
3. **Excel Validation** - Cross-references data with Excel files
4. **Evidence Generation** - Creates screenshots and proof of resolution
5. **User Notification** - Sends confirmation emails with evidence

## Technology Stack

- **AI Reasoning**: OpenAI GPT-4 for issue classification
- **Database**: Python + SQLAlchemy / cx_Oracle
- **Email**: smtplib with HTML templates
- **Excel Processing**: pandas, openpyxl
- **Screenshots**: matplotlib, dataframe_image
- **Web Interface**: Flask/FastAPI
- **Background Jobs**: Celery + Redis

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your API keys and database credentials

# Run the application
python app.py
```

## Project Structure

```
wms-automation/
├── app.py                 # Main Flask application
├── agents/               # AI agents and LLM integration
├── database/            # Database models and connections
├── email_service/       # Email templates and sending logic
├── excel_validator/     # Excel processing and validation
├── screenshot_service/  # Evidence generation
├── static/             # Web UI assets
├── templates/          # HTML templates
├── tests/              # Unit tests
└── config/             # Configuration files
```

## API Endpoints

- `POST /api/report-issue` - Submit warehouse issue
- `GET /api/issue-status/{id}` - Check resolution status
- `POST /api/validate-excel` - Upload Excel for validation
- `GET /api/dashboard` - View issue dashboard

## Example Usage

```python
# Report a missing PO
response = requests.post('/api/report-issue', json={
    'message': 'PO123 is missing from ASN456',
    'user_email': 'user@warehouse.com'
})
```

The system will automatically:
1. Parse and classify the issue using AI
2. Query the database to confirm the problem
3. Take appropriate action (send emails, run scripts)
4. Validate with Excel files if needed
5. Notify the user with evidence when resolved