# 🚀 Quick Start Guide

Get the Warehouse AI Agent up and running in 5 minutes!

## 🎯 One-Command Setup

```bash
# Clone and start the system
git clone https://github.com/warehouse-ai/warehouse-agent.git
cd warehouse-agent
./start.sh
```

That's it! The system will automatically:
- Check dependencies
- Set up configuration
- Start all services (PostgreSQL, Ollama, Warehouse Agent)
- Download the AI model
- Run health checks
- Open the web interface

## 🌐 Access Points

Once running, access the system at:

- **Web Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health

## 🧪 Quick Test

Try these examples in the web interface:

1. **Missing PO**: "PO12345 is missing from the system"
2. **Quantity Mismatch**: "Quantity mismatch for ASN67890"
3. **Missing Pallet**: "Pallet PLT001 not found in warehouse"

## 📋 Requirements

- Docker & Docker Compose
- 4GB RAM minimum
- 10GB free disk space (for AI models)

## ⚙️ Configuration

Edit `.env` file for:
- Email settings (SMTP/IMAP)
- SAP system email
- Database credentials

## 🔧 Management Commands

```bash
# View system status
./start.sh status

# View logs
./start.sh logs

# Stop system
./start.sh stop

# Restart system
./start.sh restart

# Update system
./start.sh update
```

## 🆘 Troubleshooting

**System not starting?**
```bash
# Check logs
docker-compose logs

# Restart services
docker-compose restart
```

**AI not working?**
```bash
# Check Ollama model
docker-compose exec ollama ollama list

# Download model manually
docker-compose exec ollama ollama pull llama2
```

**Database issues?**
```bash
# Check database
docker-compose exec postgres pg_isready -U warehouse_user -d warehouse_db

# Reset database
docker-compose down -v
./start.sh
```

## 🎉 Next Steps

1. Configure email settings in `.env`
2. Test with real warehouse issues
3. Customize AI prompts in `app/services/ai_classifier.py`
4. Set up production deployment with HTTPS

For detailed documentation, see [README.md](README.md)