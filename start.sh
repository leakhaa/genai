#!/bin/bash

# Warehouse AI Agent - Quick Start Script
# This script sets up and starts the entire system

set -e

echo "🤖 Warehouse AI Agent - Quick Start"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_success "Docker and Docker Compose are installed"
}

# Check if .env file exists
check_env_file() {
    if [ ! -f .env ]; then
        print_warning ".env file not found. Creating from template..."
        cp .env.example .env
        print_warning "Please edit .env file with your configuration before running the system"
        echo ""
        echo "Key configurations to update:"
        echo "- Email settings (SMTP/IMAP credentials)"
        echo "- SAP email address"
        echo "- Database credentials (if needed)"
        echo ""
        read -p "Press Enter to continue after updating .env file..."
    else
        print_success ".env file found"
    fi
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    mkdir -p uploads temp excel_files screenshots ssl
    print_success "Directories created"
}

# Build and start services
start_services() {
    print_status "Building and starting services..."
    
    # Pull latest images
    docker-compose pull postgres nginx
    
    # Build the application
    docker-compose build warehouse-agent
    
    # Start services
    docker-compose up -d
    
    print_success "Services started"
}

# Wait for services to be ready
wait_for_services() {
    print_status "Waiting for services to be ready..."
    
    # Wait for PostgreSQL
    print_status "Waiting for PostgreSQL..."
    for i in {1..30}; do
        if docker-compose exec -T postgres pg_isready -U warehouse_user -d warehouse_db &> /dev/null; then
            print_success "PostgreSQL is ready"
            break
        fi
        sleep 2
        if [ $i -eq 30 ]; then
            print_error "PostgreSQL failed to start"
            exit 1
        fi
    done
    
    # Wait for Ollama
    print_status "Waiting for Ollama..."
    for i in {1..30}; do
        if curl -s http://localhost:11434/api/tags &> /dev/null; then
            print_success "Ollama is ready"
            break
        fi
        sleep 2
        if [ $i -eq 30 ]; then
            print_warning "Ollama may not be ready, but continuing..."
            break
        fi
    done
    
    # Wait for the main application
    print_status "Waiting for Warehouse AI Agent..."
    for i in {1..60}; do
        if curl -s http://localhost:8000/api/v1/health &> /dev/null; then
            print_success "Warehouse AI Agent is ready"
            break
        fi
        sleep 2
        if [ $i -eq 60 ]; then
            print_error "Warehouse AI Agent failed to start"
            docker-compose logs warehouse-agent
            exit 1
        fi
    done
}

# Download Ollama model
setup_ollama() {
    print_status "Setting up Ollama model..."
    
    # Check if model exists
    if docker-compose exec -T ollama ollama list | grep -q llama2; then
        print_success "Llama2 model already exists"
    else
        print_status "Downloading Llama2 model (this may take a while)..."
        docker-compose exec ollama ollama pull llama2
        print_success "Llama2 model downloaded"
    fi
}

# Show system status
show_status() {
    echo ""
    echo "🎉 System Status"
    echo "================"
    
    # Check service health
    if curl -s http://localhost:8000/api/v1/health | grep -q "healthy"; then
        print_success "✅ Warehouse AI Agent: Running"
    else
        print_error "❌ Warehouse AI Agent: Not responding"
    fi
    
    if docker-compose exec -T postgres pg_isready -U warehouse_user -d warehouse_db &> /dev/null; then
        print_success "✅ PostgreSQL: Running"
    else
        print_error "❌ PostgreSQL: Not responding"
    fi
    
    if curl -s http://localhost:11434/api/tags &> /dev/null; then
        print_success "✅ Ollama: Running"
    else
        print_warning "⚠️  Ollama: Not responding"
    fi
    
    echo ""
    echo "🌐 Access Points"
    echo "================"
    echo "• Web Interface: http://localhost:8000"
    echo "• API Documentation: http://localhost:8000/docs"
    echo "• Health Check: http://localhost:8000/api/v1/health"
    echo "• Nginx Proxy: http://localhost (if configured)"
    echo ""
    echo "📊 Quick Commands"
    echo "================="
    echo "• View logs: docker-compose logs -f"
    echo "• Stop system: docker-compose down"
    echo "• Restart: docker-compose restart"
    echo "• CLI access: python cli.py --help"
    echo ""
}

# Test the system
test_system() {
    print_status "Running basic system test..."
    
    # Test health endpoint
    if curl -s http://localhost:8000/api/v1/health | grep -q "healthy"; then
        print_success "Health check passed"
    else
        print_error "Health check failed"
        return 1
    fi
    
    # Test classification endpoint
    if curl -s -X POST "http://localhost:8000/api/v1/issues/classify" \
        -H "Content-Type: application/json" \
        -d '{"message": "PO123 is missing"}' | grep -q "PO_MISSING"; then
        print_success "AI classification test passed"
    else
        print_error "AI classification test failed"
        return 1
    fi
    
    print_success "Basic system tests passed"
}

# Main execution
main() {
    echo ""
    print_status "Starting Warehouse AI Agent setup..."
    echo ""
    
    # Run setup steps
    check_docker
    check_env_file
    create_directories
    start_services
    wait_for_services
    setup_ollama
    
    # Show status
    show_status
    
    # Run tests
    if test_system; then
        echo ""
        print_success "🎉 Warehouse AI Agent is ready!"
        print_status "You can now access the system at http://localhost:8000"
        echo ""
        
        # Ask if user wants to open browser
        if command -v xdg-open &> /dev/null; then
            read -p "Open web interface in browser? (y/n): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                xdg-open http://localhost:8000
            fi
        elif command -v open &> /dev/null; then
            read -p "Open web interface in browser? (y/n): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                open http://localhost:8000
            fi
        fi
    else
        print_error "System tests failed. Please check the logs."
        docker-compose logs
        exit 1
    fi
}

# Handle script arguments
case "${1:-}" in
    "stop")
        print_status "Stopping Warehouse AI Agent..."
        docker-compose down
        print_success "Services stopped"
        ;;
    "restart")
        print_status "Restarting Warehouse AI Agent..."
        docker-compose restart
        wait_for_services
        show_status
        ;;
    "logs")
        docker-compose logs -f
        ;;
    "status")
        show_status
        ;;
    "test")
        test_system
        ;;
    "update")
        print_status "Updating Warehouse AI Agent..."
        docker-compose pull
        docker-compose build warehouse-agent
        docker-compose up -d
        wait_for_services
        print_success "Update completed"
        ;;
    *)
        main
        ;;
esac