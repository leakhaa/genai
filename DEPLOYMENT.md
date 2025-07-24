# WMS Automation System - Deployment Guide

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Oracle Database (or PostgreSQL as alternative)
- Redis server (for background jobs)
- SMTP server access (for email notifications)
- OpenAI API key

### 1. Environment Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd wms-automation

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your configuration
nano .env
```

Required environment variables:
- `OPENAI_API_KEY`: Your OpenAI API key
- `DB_HOST`, `DB_USER`, `DB_PASSWORD`: Database connection details
- `SMTP_SERVER`, `SMTP_USERNAME`, `SMTP_PASSWORD`: Email server details

### 3. Database Setup

```bash
# For Oracle database
python -c "from database.connection import initialize_database; db = initialize_database(use_oracle=True); db.create_tables()"

# For PostgreSQL database
python -c "from database.connection import initialize_database; db = initialize_database(use_oracle=False); db.create_tables()"
```

### 4. Start the Application

```bash
# Development mode
python app.py

# Production mode (with gunicorn)
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### 5. Test the System

```bash
# Run comprehensive tests
python test_system.py

# Or access the web dashboard
open http://localhost:5000
```

## 🏗️ Production Deployment

### Docker Deployment

1. **Create Dockerfile**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

2. **Build and Run**:
```bash
docker build -t wms-automation .
docker run -p 5000:5000 --env-file .env wms-automation
```

### Kubernetes Deployment

1. **Create ConfigMap**:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: wms-config
data:
  FLASK_ENV: "production"
  DB_HOST: "your-db-host"
  SMTP_SERVER: "your-smtp-server"
```

2. **Create Secret**:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: wms-secrets
type: Opaque
stringData:
  OPENAI_API_KEY: "your-openai-key"
  DB_PASSWORD: "your-db-password"
  SMTP_PASSWORD: "your-smtp-password"
```

3. **Create Deployment**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: wms-automation
spec:
  replicas: 3
  selector:
    matchLabels:
      app: wms-automation
  template:
    metadata:
      labels:
        app: wms-automation
    spec:
      containers:
      - name: wms-automation
        image: wms-automation:latest
        ports:
        - containerPort: 5000
        envFrom:
        - configMapRef:
            name: wms-config
        - secretRef:
            name: wms-secrets
```

### Nginx Configuration

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /path/to/wms-automation/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

## 🔧 System Configuration

### Database Configuration

#### Oracle Database
```python
# Required PL/SQL procedures
CREATE OR REPLACE PROCEDURE WMS_MISSING_ASN_PROC(p_asn_id VARCHAR2) AS
BEGIN
    -- Your ASN processing logic here
    DBMS_OUTPUT.PUT_LINE('Processing missing ASN: ' || p_asn_id);
END;

CREATE OR REPLACE PROCEDURE WMS_MISSING_PO_PROC(p_po_id VARCHAR2, p_asn_id VARCHAR2) AS
BEGIN
    -- Your PO processing logic here
    DBMS_OUTPUT.PUT_LINE('Processing missing PO: ' || p_po_id);
END;

CREATE OR REPLACE PROCEDURE WMS_MISSING_PALLET_PROC(p_pallet_id VARCHAR2, p_po_id VARCHAR2) AS
BEGIN
    -- Your pallet processing logic here
    DBMS_OUTPUT.PUT_LINE('Processing missing pallet: ' || p_pallet_id);
END;

CREATE OR REPLACE PROCEDURE WMS_QUANTITY_RECONCILE_PROC(p_po_id VARCHAR2) AS
BEGIN
    -- Your quantity reconciliation logic here
    DBMS_OUTPUT.PUT_LINE('Reconciling quantities for PO: ' || p_po_id);
END;
```

#### PostgreSQL Database
```sql
-- Create stored procedures for PostgreSQL
CREATE OR REPLACE FUNCTION wms_missing_asn_proc(p_asn_id VARCHAR)
RETURNS VOID AS $$
BEGIN
    -- Your ASN processing logic here
    RAISE NOTICE 'Processing missing ASN: %', p_asn_id;
END;
$$ LANGUAGE plpgsql;
```

### Email Templates

Customize email templates in `email_service/templates/`:
- `sap_missing_asn.html`: Missing ASN notifications
- `sap_missing_po.html`: Missing PO notifications  
- `quantity_mismatch.html`: Quantity mismatch alerts
- `resolution_notification.html`: Resolution confirmations
- `manual_review.html`: Manual review requests

### AI Model Configuration

Fine-tune the AI classifier in `agents/issue_classifier.py`:
- Adjust temperature for creativity vs consistency
- Modify system prompts for better classification
- Add custom validation rules
- Extend issue types and actions

## 📊 Monitoring and Logging

### Logging Configuration

```python
# In config/settings.py
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
LOG_FILE = "logs/wms_automation.log"
```

### Health Checks

```bash
# System health endpoint
curl http://localhost:5000/api/health

# Database connection test
python -c "from database.connection import get_db_manager; print(get_db_manager().test_connection())"

# Email service test
python -c "from email_service.email_sender import email_service; print(email_service.test_email_connection())"
```

### Performance Monitoring

1. **Application Metrics**:
   - Issue processing time
   - AI classification accuracy
   - Email delivery success rate
   - Database query performance

2. **System Metrics**:
   - CPU and memory usage
   - Database connection pool status
   - Redis queue length
   - HTTP response times

## 🔒 Security Considerations

### Environment Variables
- Never commit `.env` files to version control
- Use secure secret management in production
- Rotate API keys and passwords regularly

### Database Security
- Use dedicated database user with minimal privileges
- Enable database connection encryption
- Implement proper backup and recovery procedures

### API Security
- Implement rate limiting
- Add authentication for sensitive endpoints
- Use HTTPS in production
- Validate all input data

### Email Security
- Use secure SMTP connections (TLS/SSL)
- Implement email rate limiting
- Sanitize email content to prevent injection

## 🚨 Troubleshooting

### Common Issues

1. **Database Connection Errors**:
   ```bash
   # Check database connectivity
   python -c "from database.connection import get_db_manager; get_db_manager().test_connection()"
   ```

2. **OpenAI API Errors**:
   ```bash
   # Verify API key
   python -c "import openai; openai.api_key='your-key'; print(openai.Model.list())"
   ```

3. **Email Delivery Issues**:
   ```bash
   # Test SMTP connection
   python -c "from email_service.email_sender import email_service; print(email_service.test_email_connection())"
   ```

4. **Excel Validation Errors**:
   - Check file format (xlsx, xls, csv)
   - Verify column names match expected mappings
   - Ensure numeric data in quantity columns

### Log Analysis

```bash
# Monitor application logs
tail -f logs/wms_automation.log

# Filter for errors
grep "ERROR" logs/wms_automation.log

# Check AI classification logs
grep "classification" logs/wms_automation.log
```

## 📈 Scaling and Optimization

### Horizontal Scaling
- Deploy multiple application instances behind a load balancer
- Use Redis for session storage and caching
- Implement database read replicas for better performance

### Performance Optimization
- Enable database query caching
- Implement API response caching
- Use background jobs for heavy processing
- Optimize AI model calls with batching

### Database Optimization
- Create proper indexes on frequently queried columns
- Implement database partitioning for large tables
- Use connection pooling for better resource utilization
- Regular database maintenance and statistics updates

## 🔄 Backup and Recovery

### Database Backup
```bash
# Oracle backup
expdp username/password@database directory=backup_dir dumpfile=wms_backup.dmp

# PostgreSQL backup
pg_dump -h localhost -U username -d wms_db > wms_backup.sql
```

### Application Backup
```bash
# Backup configuration and logs
tar -czf wms_backup_$(date +%Y%m%d).tar.gz .env logs/ uploads/ screenshots/
```

### Recovery Procedures
1. Restore database from backup
2. Restore application configuration
3. Restart all services
4. Verify system functionality with test script

## 📞 Support and Maintenance

### Regular Maintenance Tasks
- Monitor system performance and logs
- Update dependencies and security patches
- Review and optimize AI model performance
- Clean up old logs and temporary files
- Test backup and recovery procedures

### Support Contacts
- **Technical Issues**: IT Support Team
- **Process Issues**: Operations Manager  
- **AI/ML Issues**: Data Science Team
- **Critical Issues**: Management Team

For additional support, refer to the system documentation and contact the development team.