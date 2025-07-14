#!/bin/bash

# AI Background Remover - Setup Script
# This script automates the setup process for the AI background removal tool

set -e  # Exit on any error

echo "🚀 AI Background Remover Setup Script"
echo "======================================"

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

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root for security reasons"
   exit 1
fi

# Detect operating system
OS=""
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    OS="windows"
else
    print_error "Unsupported operating system: $OSTYPE"
    exit 1
fi

print_status "Detected OS: $OS"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check for required dependencies
print_status "Checking dependencies..."

# Check Python
if ! command_exists python3; then
    print_error "Python 3 is required but not installed. Please install Python 3.9 or later."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.9"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)"; then
    print_error "Python 3.9+ is required. Current version: $PYTHON_VERSION"
    exit 1
fi

print_success "Python $PYTHON_VERSION detected"

# Check pip
if ! command_exists pip3; then
    print_error "pip3 is required but not installed."
    exit 1
fi

# Check Docker (optional)
DOCKER_AVAILABLE=false
if command_exists docker; then
    DOCKER_AVAILABLE=true
    print_success "Docker detected"
else
    print_warning "Docker not found. Manual installation will be used."
fi

# Check Docker Compose (optional)
COMPOSE_AVAILABLE=false
if command_exists docker-compose || docker compose version >/dev/null 2>&1; then
    COMPOSE_AVAILABLE=true
    print_success "Docker Compose detected"
fi

# Setup method selection
echo ""
echo "Choose installation method:"
echo "1) Docker Compose (Recommended - includes Redis, Nginx, auto-scaling)"
echo "2) Docker only (Simple container deployment)"
echo "3) Manual installation (Local development)"

if [[ "$DOCKER_AVAILABLE" == false ]]; then
    print_warning "Docker not available. Using manual installation."
    SETUP_METHOD=3
else
    read -p "Enter your choice (1-3): " SETUP_METHOD
fi

case $SETUP_METHOD in
    1)
        if [[ "$COMPOSE_AVAILABLE" == false ]]; then
            print_error "Docker Compose is required for this option"
            exit 1
        fi
        print_status "Using Docker Compose deployment"
        ;;
    2)
        print_status "Using Docker-only deployment"
        ;;
    3)
        print_status "Using manual installation"
        ;;
    *)
        print_error "Invalid choice"
        exit 1
        ;;
esac

# Create environment file
print_status "Setting up environment configuration..."

if [[ ! -f .env ]]; then
    cp .env.example .env
    print_success "Created .env file from template"
    
    # Generate secret key
    SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
    
    if [[ "$OS" == "macos" ]]; then
        sed -i '' "s/your-secret-key-here/$SECRET_KEY/" .env
    else
        sed -i "s/your-secret-key-here/$SECRET_KEY/" .env
    fi
    
    print_success "Generated secure secret key"
else
    print_warning ".env file already exists, skipping creation"
fi

# Setup based on chosen method
case $SETUP_METHOD in
    1)
        print_status "Starting Docker Compose deployment..."
        
        # Build and start services
        docker-compose build
        docker-compose up -d
        
        print_status "Waiting for services to start..."
        sleep 10
        
        # Check if services are running
        if docker-compose ps | grep -q "Up"; then
            print_success "Services started successfully!"
            echo ""
            echo "🌐 Access your application:"
            echo "   Web Interface: http://localhost"
            echo "   API: http://localhost/api"
            echo "   Health Check: http://localhost/api/health"
        else
            print_error "Some services failed to start. Check logs with: docker-compose logs"
            exit 1
        fi
        ;;
        
    2)
        print_status "Building Docker image..."
        docker build -t ai-background-remover .
        
        print_status "Starting Redis container..."
        docker run -d --name bg-remover-redis -p 6379:6379 redis:7-alpine
        
        print_status "Starting application container..."
        docker run -d --name bg-remover-app \
            -p 5000:5000 \
            -e REDIS_URL=redis://host.docker.internal:6379 \
            --link bg-remover-redis:redis \
            ai-background-remover
        
        print_success "Docker containers started!"
        echo ""
        echo "🌐 Access your application:"
        echo "   Web Interface: http://localhost:5000"
        echo "   API: http://localhost:5000/api"
        echo "   Health Check: http://localhost:5000/api/health"
        ;;
        
    3)
        print_status "Installing Python dependencies..."
        
        # Create virtual environment if it doesn't exist
        if [[ ! -d "venv" ]]; then
            python3 -m venv venv
            print_success "Created virtual environment"
        fi
        
        # Activate virtual environment
        source venv/bin/activate
        
        # Upgrade pip
        pip install --upgrade pip
        
        # Install requirements
        pip install -r requirements.txt
        print_success "Python dependencies installed"
        
        # Check for Redis
        print_status "Checking Redis installation..."
        
        if ! command_exists redis-server; then
            print_warning "Redis not found. Installing Redis..."
            
            case $OS in
                "linux")
                    if command_exists apt-get; then
                        sudo apt-get update
                        sudo apt-get install -y redis-server
                    elif command_exists yum; then
                        sudo yum install -y redis
                    elif command_exists pacman; then
                        sudo pacman -S redis
                    else
                        print_error "Cannot install Redis automatically. Please install Redis manually."
                        exit 1
                    fi
                    ;;
                "macos")
                    if command_exists brew; then
                        brew install redis
                    else
                        print_error "Homebrew not found. Please install Redis manually: https://redis.io/download"
                        exit 1
                    fi
                    ;;
            esac
            
            print_success "Redis installed"
        else
            print_success "Redis already installed"
        fi
        
        # Start Redis
        print_status "Starting Redis..."
        if [[ "$OS" == "linux" ]]; then
            sudo systemctl start redis-server || redis-server --daemonize yes
        elif [[ "$OS" == "macos" ]]; then
            brew services start redis || redis-server --daemonize yes
        fi
        
        print_success "Manual installation completed!"
        echo ""
        echo "🚀 To start the application:"
        echo "   1. Start the Flask app: python app.py"
        echo "   2. Start Celery worker: celery -A app.celery worker --loglevel=info"
        echo ""
        echo "🌐 Then access your application:"
        echo "   Web Interface: http://localhost:5000"
        echo "   API: http://localhost:5000/api"
        ;;
esac

# Performance recommendations
echo ""
print_status "Performance Recommendations:"

if command_exists nvidia-smi; then
    print_success "NVIDIA GPU detected - GPU acceleration available"
    echo "   Set CUDA_VISIBLE_DEVICES=0 in .env to enable GPU"
else
    print_warning "No NVIDIA GPU detected - CPU processing only"
    echo "   Consider using a GPU for faster processing"
fi

# Check available memory
if [[ "$OS" == "linux" ]]; then
    MEMORY_GB=$(free -g | awk '/^Mem:/{print $2}')
    if [[ $MEMORY_GB -lt 4 ]]; then
        print_warning "Low memory detected ($MEMORY_GB GB). Consider upgrading for better performance."
    else
        print_success "Sufficient memory detected ($MEMORY_GB GB)"
    fi
fi

# Security recommendations
echo ""
print_status "Security Recommendations:"
echo "   1. Change default secret key in .env"
echo "   2. Set up SSL/TLS for production"
echo "   3. Configure firewall rules"
echo "   4. Set up rate limiting"
echo "   5. Regular security updates"

# Final instructions
echo ""
print_success "Setup completed successfully! 🎉"
echo ""
echo "📚 Next steps:"
echo "   1. Read the README.md for detailed usage instructions"
echo "   2. Test the application with a sample image"
echo "   3. Configure additional settings in .env as needed"
echo "   4. Set up monitoring and logging for production"
echo ""
echo "💡 Need help? Check the troubleshooting section in README.md"
echo ""

# Final health check
if [[ $SETUP_METHOD -eq 1 ]] || [[ $SETUP_METHOD -eq 2 ]]; then
    print_status "Performing health check..."
    sleep 5
    
    if [[ $SETUP_METHOD -eq 1 ]]; then
        HEALTH_URL="http://localhost/api/health"
    else
        HEALTH_URL="http://localhost:5000/api/health"
    fi
    
    if command_exists curl; then
        if curl -s "$HEALTH_URL" > /dev/null; then
            print_success "Health check passed! Application is running."
        else
            print_warning "Health check failed. Application might still be starting up."
        fi
    fi
fi

echo "Happy background removing! 🖼️✨"