"""Main FastAPI application for the Warehouse AI Agent."""

import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.config import settings
from app.api.routes import router

# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=settings.log_level
)

# Create necessary directories
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(settings.temp_dir, exist_ok=True)
os.makedirs(settings.excel_dir, exist_ok=True)
os.makedirs(settings.screenshots_dir, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("🚀 Starting Warehouse AI Agent...")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"Database type: {settings.db_type}")
    logger.info(f"Using Ollama: {settings.use_ollama}")
    
    # Test database connection
    try:
        from app.services.database_service import database_service
        db_healthy = await database_service.health_check()
        if db_healthy:
            logger.info("✅ Database connection successful")
        else:
            logger.warning("⚠️ Database connection failed")
    except Exception as e:
        logger.error(f"❌ Database initialization error: {e}")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Warehouse AI Agent...")


# Create FastAPI app
app = FastAPI(
    title="Warehouse AI Agent",
    description="""
    Intelligent AI-powered warehouse automation system for resolving issues related to 
    missing ASN, PO, pallets, and quantity mismatches using LLMs, mail automation, 
    PL/SQL triggers, Excel validation, and database integration.
    
    ## Features
    
    * 🧠 **AI-Powered Classification**: Uses LLM to understand and classify warehouse issues
    * 📧 **SAP Integration**: Automated email communication with SAP systems
    * 📊 **Excel Validation**: Process and validate Excel files from SAP
    * 🗄️ **Database Management**: PL/SQL operations for data correction
    * 📈 **Visual Reports**: Generate screenshots and comparison tables
    * 🔄 **End-to-End Automation**: Minimal human intervention required
    
    ## Supported Issue Types
    
    * **ASN_MISSING**: Missing Advanced Shipping Notice
    * **PO_MISSING**: Missing Purchase Order
    * **PALLET_MISSING**: Missing pallets requiring validation
    * **QUANTITY_MISMATCH**: Quantity discrepancies between systems
    """,
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1", tags=["Warehouse AI Agent"])

# Serve static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with HTML interface."""
    return HTMLResponse(content="""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Warehouse AI Agent</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            color: white;
            margin-bottom: 40px;
        }
        
        .header h1 {
            font-size: 3rem;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .header p {
            font-size: 1.2rem;
            opacity: 0.9;
        }
        
        .cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        
        .card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 35px rgba(0,0,0,0.3);
        }
        
        .card h3 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 1.5rem;
        }
        
        .card p {
            color: #666;
            margin-bottom: 15px;
        }
        
        .btn {
            display: inline-block;
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            padding: 12px 25px;
            border-radius: 25px;
            text-decoration: none;
            transition: all 0.3s ease;
            border: none;
            cursor: pointer;
            font-size: 1rem;
        }
        
        .btn:hover {
            transform: scale(1.05);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        
        .demo-form {
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 30px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #333;
        }
        
        .form-group input,
        .form-group textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #e1e1e1;
            border-radius: 8px;
            font-size: 1rem;
            transition: border-color 0.3s ease;
        }
        
        .form-group input:focus,
        .form-group textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .form-group textarea {
            height: 120px;
            resize: vertical;
        }
        
        .status-display {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            margin-top: 20px;
            border-left: 4px solid #667eea;
        }
        
        .feature-list {
            list-style: none;
            margin-top: 15px;
        }
        
        .feature-list li {
            padding: 5px 0;
            position: relative;
            padding-left: 25px;
        }
        
        .feature-list li:before {
            content: "✅";
            position: absolute;
            left: 0;
        }
        
        .footer {
            text-align: center;
            color: white;
            margin-top: 40px;
            opacity: 0.8;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Warehouse AI Agent</h1>
            <p>Intelligent automation for warehouse issue resolution</p>
        </div>
        
        <div class="cards">
            <div class="card">
                <h3>🧠 AI-Powered Classification</h3>
                <p>Advanced LLM technology automatically understands and classifies warehouse issues from natural language descriptions.</p>
                <ul class="feature-list">
                    <li>ASN Missing detection</li>
                    <li>PO Missing identification</li>
                    <li>Pallet discrepancy analysis</li>
                    <li>Quantity mismatch recognition</li>
                </ul>
            </div>
            
            <div class="card">
                <h3>📧 SAP Integration</h3>
                <p>Seamless email-based communication with SAP systems for automated data retrieval and issue resolution.</p>
                <ul class="feature-list">
                    <li>Automated email requests</li>
                    <li>Excel file processing</li>
                    <li>Response monitoring</li>
                    <li>Error handling</li>
                </ul>
            </div>
            
            <div class="card">
                <h3>🗄️ Database Management</h3>
                <p>Intelligent database operations with PL/SQL procedures for data validation and correction.</p>
                <ul class="feature-list">
                    <li>Missing pallet insertion</li>
                    <li>Quantity corrections</li>
                    <li>Audit trail logging</li>
                    <li>Data validation</li>
                </ul>
            </div>
            
            <div class="card">
                <h3>📊 Visual Reports</h3>
                <p>Comprehensive reporting with screenshots, tables, and visual comparisons for clear issue resolution tracking.</p>
                <ul class="feature-list">
                    <li>Validation screenshots</li>
                    <li>Comparison tables</li>
                    <li>Summary charts</li>
                    <li>Email notifications</li>
                </ul>
            </div>
        </div>
        
        <div class="demo-form">
            <h3>🔍 Try the AI Classifier</h3>
            <p>Test the AI classification system with your warehouse issue description:</p>
            
            <div class="form-group">
                <label for="userEmail">Your Email:</label>
                <input type="email" id="userEmail" placeholder="your.email@company.com" value="user@example.com">
            </div>
            
            <div class="form-group">
                <label for="issueMessage">Issue Description:</label>
                <textarea id="issueMessage" placeholder="Describe your warehouse issue... (e.g., 'PO123 is missing' or 'Quantity mismatch for ASN456')">PO12345 is missing from the system</textarea>
            </div>
            
            <button class="btn" onclick="classifyIssue()">🧠 Classify Issue</button>
            <button class="btn" onclick="submitIssue()" style="margin-left: 10px;">🚀 Submit for Processing</button>
            
            <div id="result" class="status-display" style="display: none;">
                <!-- Results will appear here -->
            </div>
        </div>
        
        <div class="cards">
            <div class="card">
                <h3>📖 API Documentation</h3>
                <p>Explore the complete API documentation with interactive examples and detailed endpoint descriptions.</p>
                <a href="/docs" class="btn">View API Docs</a>
            </div>
            
            <div class="card">
                <h3>📊 System Health</h3>
                <p>Monitor system status, active issues, and performance metrics in real-time.</p>
                <button class="btn" onclick="checkHealth()">Check Health</button>
            </div>
            
            <div class="card">
                <h3>📈 Statistics</h3>
                <p>View comprehensive statistics about issue types, resolution rates, and system performance.</p>
                <button class="btn" onclick="getStats()">View Stats</button>
            </div>
        </div>
        
        <div class="footer">
            <p>© 2024 Warehouse AI Agent - Powered by AI, Built for Efficiency</p>
        </div>
    </div>

    <script>
        async function classifyIssue() {
            const message = document.getElementById('issueMessage').value;
            const resultDiv = document.getElementById('result');
            
            if (!message.trim()) {
                alert('Please enter an issue description');
                return;
            }
            
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = '<p>🔄 Classifying issue...</p>';
            
            try {
                const response = await fetch('/api/v1/issues/classify', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ message: message })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    resultDiv.innerHTML = `
                        <h4>🎯 Classification Results</h4>
                        <p><strong>Issue Type:</strong> ${data.classification.issue_type}</p>
                        <p><strong>Action Required:</strong> ${data.classification.action}</p>
                        <p><strong>Confidence:</strong> ${(data.classification.confidence_score * 100).toFixed(1)}%</p>
                        <p><strong>PO ID:</strong> ${data.classification.po_id || 'Not detected'}</p>
                        <p><strong>ASN ID:</strong> ${data.classification.asn_id || 'Not detected'}</p>
                        <p><strong>Requires Excel:</strong> ${data.classification.requires_excel ? 'Yes' : 'No'}</p>
                    `;
                } else {
                    resultDiv.innerHTML = `<p>❌ Error: ${data.detail}</p>`;
                }
            } catch (error) {
                resultDiv.innerHTML = `<p>❌ Network error: ${error.message}</p>`;
            }
        }
        
        async function submitIssue() {
            const email = document.getElementById('userEmail').value;
            const message = document.getElementById('issueMessage').value;
            const resultDiv = document.getElementById('result');
            
            if (!email.trim() || !message.trim()) {
                alert('Please enter both email and issue description');
                return;
            }
            
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = '<p>🚀 Submitting issue for processing...</p>';
            
            try {
                const response = await fetch('/api/v1/issues/submit', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        message: message,
                        user_email: email
                    })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    resultDiv.innerHTML = `
                        <h4>✅ Issue Submitted Successfully</h4>
                        <p><strong>Issue ID:</strong> ${data.issue_id}</p>
                        <p><strong>Status:</strong> ${data.status}</p>
                        <p><strong>Classification:</strong> ${data.classification.issue_type}</p>
                        <p><strong>Action:</strong> ${data.classification.action}</p>
                        <p><em>You will receive email notifications about the resolution progress.</em></p>
                        <button class="btn" onclick="checkIssueStatus('${data.issue_id}')" style="margin-top: 10px;">Check Status</button>
                    `;
                } else {
                    resultDiv.innerHTML = `<p>❌ Error: ${data.detail}</p>`;
                }
            } catch (error) {
                resultDiv.innerHTML = `<p>❌ Network error: ${error.message}</p>`;
            }
        }
        
        async function checkIssueStatus(issueId) {
            const resultDiv = document.getElementById('result');
            resultDiv.innerHTML = '<p>🔄 Checking issue status...</p>';
            
            try {
                const response = await fetch(`/api/v1/issues/${issueId}/status`);
                const data = await response.json();
                
                if (response.ok) {
                    resultDiv.innerHTML = `
                        <h4>📊 Issue Status</h4>
                        <p><strong>Issue ID:</strong> ${data.issue_id}</p>
                        <p><strong>Status:</strong> ${data.status}</p>
                        <p><strong>Created:</strong> ${new Date(data.created_at).toLocaleString()}</p>
                        <p><strong>Updated:</strong> ${new Date(data.updated_at).toLocaleString()}</p>
                        ${data.resolution_summary ? `<p><strong>Summary:</strong> ${data.resolution_summary}</p>` : ''}
                        <p><strong>Actions Taken:</strong> ${data.actions_taken.length}</p>
                    `;
                } else {
                    resultDiv.innerHTML = `<p>❌ Error: ${data.detail}</p>`;
                }
            } catch (error) {
                resultDiv.innerHTML = `<p>❌ Network error: ${error.message}</p>`;
            }
        }
        
        async function checkHealth() {
            const resultDiv = document.getElementById('result');
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = '<p>🔄 Checking system health...</p>';
            
            try {
                const response = await fetch('/api/v1/health');
                const data = await response.json();
                
                resultDiv.innerHTML = `
                    <h4>🏥 System Health Status</h4>
                    <p><strong>Warehouse Agent:</strong> ${data.warehouse_agent}</p>
                    <p><strong>Database:</strong> ${data.database ? '✅ Healthy' : '❌ Unhealthy'}</p>
                    <p><strong>Active Issues:</strong> ${data.active_resolutions || 0}</p>
                    <p><strong>Timestamp:</strong> ${data.timestamp}</p>
                `;
            } catch (error) {
                resultDiv.innerHTML = `<p>❌ Network error: ${error.message}</p>`;
            }
        }
        
        async function getStats() {
            const resultDiv = document.getElementById('result');
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = '<p>🔄 Loading statistics...</p>';
            
            try {
                const response = await fetch('/api/v1/stats');
                const data = await response.json();
                
                let statusBreakdown = '';
                for (const [status, count] of Object.entries(data.status_breakdown || {})) {
                    statusBreakdown += `<li>${status}: ${count}</li>`;
                }
                
                let typeBreakdown = '';
                for (const [type, count] of Object.entries(data.issue_type_breakdown || {})) {
                    typeBreakdown += `<li>${type}: ${count}</li>`;
                }
                
                resultDiv.innerHTML = `
                    <h4>📈 System Statistics</h4>
                    <p><strong>Total Active Issues:</strong> ${data.total_active_issues}</p>
                    <div style="margin-top: 15px;">
                        <strong>Status Breakdown:</strong>
                        <ul style="margin: 5px 0 0 20px;">${statusBreakdown || '<li>No active issues</li>'}</ul>
                    </div>
                    <div style="margin-top: 15px;">
                        <strong>Issue Type Breakdown:</strong>
                        <ul style="margin: 5px 0 0 20px;">${typeBreakdown || '<li>No active issues</li>'}</ul>
                    </div>
                `;
            } catch (error) {
                resultDiv.innerHTML = `<p>❌ Network error: ${error.message}</p>`;
            }
        }
    </script>
</body>
</html>
    """)


@app.get("/favicon.ico")
async def favicon():
    """Favicon endpoint."""
    return {"message": "🤖"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )