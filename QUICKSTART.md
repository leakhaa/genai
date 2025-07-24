# 🚀 WMS Automation System - Quick Start Guide

## ✅ System Status: **RUNNING**

Your AI-powered Warehouse Management System automation is now **live and operational**!

## 🌐 Access Points

- **Web Dashboard**: http://localhost:5000
- **API Health Check**: http://localhost:5000/api/health
- **API Documentation**: All endpoints listed below

## 🧪 What's Working Right Now

✅ **Core System**: Flask server running on port 5000  
✅ **Database**: SQLite database with all tables created  
✅ **Web Dashboard**: Beautiful UI for issue management  
✅ **API Endpoints**: All REST endpoints functional  
✅ **Excel Validation**: File upload and validation working  
✅ **Warehouse Data**: PO/ASN/Pallet data retrieval  
✅ **Logging**: Structured logging with Loguru  
✅ **Error Handling**: Graceful error handling throughout  

## 🔧 Current Limitations

⚠️ **AI Classification**: Requires OpenAI API key (see setup below)  
⚠️ **Email Notifications**: Requires SMTP configuration  
⚠️ **Production Database**: Currently using SQLite (Oracle/PostgreSQL for production)  

## 🚀 Quick Test

Run the demo test to verify everything is working:

```bash
# In the project directory
source wms_env/bin/activate
python3 demo_test.py
```

## 🔑 Enable AI Features (Optional)

To enable AI-powered issue classification, add your OpenAI API key:

```bash
# Edit .env file
nano .env

# Add your OpenAI API key
OPENAI_API_KEY=your-actual-openai-api-key-here
```

Then restart the server:
```bash
# Stop current server (Ctrl+C if running in foreground)
# Restart
source wms_env/bin/activate
python3 app.py
```

## 📊 Available API Endpoints

### Core Operations
- `GET /api/health` - System health check
- `GET /api/dashboard` - Dashboard statistics
- `POST /api/report-issue` - Report new warehouse issue
- `GET /api/issue-status/{id}` - Get issue status

### Data Operations
- `POST /api/validate-excel` - Upload and validate Excel files
- `GET /api/warehouse-data/{type}/{id}` - Get warehouse data (ASN/PO/Pallet)
- `GET /api/user-issues/{email}` - Get user's issues

## 🎯 Example Usage

### Report an Issue (with AI classification)
```bash
curl -X POST http://localhost:5000/api/report-issue \
  -H "Content-Type: application/json" \
  -d '{
    "message": "ASN ASN123 is missing from the system",
    "user_email": "warehouse@company.com"
  }'
```

### Validate Excel File
```bash
curl -X POST http://localhost:5000/api/validate-excel \
  -F "file=@your_warehouse_data.xlsx" \
  -F "po_id=PO123"
```

### Get Dashboard Data
```bash
curl http://localhost:5000/api/dashboard
```

## 🏭 System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Dashboard │    │   Flask API      │    │   AI Classifier │
│   (Port 5000)   │◄──►│   (REST)         │◄──►│   (GPT-4)       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                       ┌────────▼────────┐
                       │   SQLite DB     │
                       │   (Development) │
                       └─────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │   Background Services │
                    │   • Email Sender      │
                    │   • Excel Validator   │
                    │   • Screenshot Gen    │
                    │   • PL/SQL Executor   │
                    └───────────────────────┘
```

## 📁 Project Structure

```
wms-automation/
├── app.py                    # Main Flask application
├── demo_test.py             # Quick functionality test
├── test_system.py           # Comprehensive test suite
├── config/
│   └── settings.py          # Configuration management
├── database/
│   ├── models.py            # SQLAlchemy ORM models
│   ├── connection.py        # Database connection
│   └── services.py          # Business logic services
├── agents/
│   └── issue_classifier.py # AI-powered issue classification
├── email_service/
│   ├── email_sender.py      # Email automation
│   └── templates/           # HTML email templates
├── excel_validator/
│   └── validator.py         # Excel file validation
├── screenshot_service/
│   └── generator.py         # Evidence screenshot generation
├── templates/
│   └── dashboard.html       # Web dashboard UI
├── uploads/                 # File upload directory
├── logs/                    # Application logs
└── screenshots/             # Generated screenshots
```

## 🔄 Next Steps for Production

1. **Database Migration**: Switch to Oracle or PostgreSQL
2. **Environment Configuration**: Set up production environment variables
3. **Email Configuration**: Configure SMTP for notifications
4. **Security**: Add authentication and authorization
5. **Monitoring**: Set up application monitoring
6. **Scaling**: Deploy with Gunicorn/uWSGI behind Nginx

## 🆘 Troubleshooting

### Server Won't Start
```bash
# Check if port 5000 is in use
lsof -i :5000

# Kill existing process if needed
kill -9 <PID>

# Restart server
source wms_env/bin/activate
python3 app.py
```

### Database Issues
```bash
# Recreate database
python3 -c "from database.connection import initialize_database; initialize_database()"
```

### Import Errors
```bash
# Reinstall dependencies
source wms_env/bin/activate
pip install -r requirements.txt
```

## 📞 Support

- Check `logs/wms_automation.log` for detailed error messages
- Run `python3 demo_test.py` to verify basic functionality
- Review `DEPLOYMENT.md` for detailed deployment instructions

---

**🎉 Congratulations! Your WMS Automation System is ready to streamline warehouse operations!**