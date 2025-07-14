#!/bin/bash

# Background Removal Application Setup Script
set -e

echo "🎨 Setting up AI Background Removal Application..."
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_blue() {
    echo -e "${BLUE}[SETUP]${NC} $1"
}

# Check if running on supported OS
check_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        OS="windows"
    else
        print_error "Unsupported operating system: $OSTYPE"
        exit 1
    fi
    print_status "Detected OS: $OS"
}

# Check prerequisites
check_prerequisites() {
    print_blue "Checking prerequisites..."
    
    # Check Docker
    if command -v docker &> /dev/null; then
        print_status "Docker is installed: $(docker --version)"
    else
        print_error "Docker is not installed. Please install Docker first."
        echo "Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    # Check Docker Compose
    if command -v docker-compose &> /dev/null; then
        print_status "Docker Compose is installed: $(docker-compose --version)"
    else
        print_warning "Docker Compose not found. Checking for docker compose plugin..."
        if docker compose version &> /dev/null; then
            print_status "Docker Compose plugin is available"
            alias docker-compose="docker compose"
        else
            print_error "Docker Compose is not available. Please install Docker Compose."
            exit 1
        fi
    fi
    
    # Check NVIDIA Docker (optional)
    if command -v nvidia-docker &> /dev/null || docker info | grep -i nvidia &> /dev/null; then
        print_status "NVIDIA Docker support detected"
        GPU_SUPPORT=true
    else
        print_warning "NVIDIA Docker not detected. GPU acceleration will not be available."
        GPU_SUPPORT=false
    fi
    
    # Check Python (for manual installation)
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version)
        print_status "Python is installed: $PYTHON_VERSION"
    else
        print_warning "Python 3 not found. Required for manual installation."
    fi
    
    # Check Node.js (for Node.js version)
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        print_status "Node.js is installed: $NODE_VERSION"
    else
        print_warning "Node.js not found. Required for Node.js version."
    fi
}

# Setup environment
setup_environment() {
    print_blue "Setting up environment..."
    
    # Create environment file if it doesn't exist
    if [ ! -f .env ]; then
        print_status "Creating .env file from template..."
        cp .env.example .env
        
        # Generate random secret key
        if command -v openssl &> /dev/null; then
            SECRET_KEY=$(openssl rand -hex 32)
            sed -i.bak "s/your-super-secret-key-change-in-production/$SECRET_KEY/" .env
            print_status "Generated random SECRET_KEY"
        else
            print_warning "OpenSSL not found. Please manually set SECRET_KEY in .env file"
        fi
    else
        print_status ".env file already exists"
    fi
    
    # Create necessary directories
    mkdir -p uploads outputs models public
    print_status "Created necessary directories"
}

# Choose installation method
choose_installation() {
    echo ""
    print_blue "Choose installation method:"
    echo "1) Docker (Recommended) - Python/Flask version"
    echo "2) Docker - Node.js/Express version"
    echo "3) Manual Python installation"
    echo "4) Manual Node.js installation"
    echo "5) Development setup with hot reload"
    echo ""
    read -p "Enter your choice (1-5): " choice
    
    case $choice in
        1)
            install_docker_python
            ;;
        2)
            install_docker_nodejs
            ;;
        3)
            install_manual_python
            ;;
        4)
            install_manual_nodejs
            ;;
        5)
            install_development
            ;;
        *)
            print_error "Invalid choice. Please run the script again."
            exit 1
            ;;
    esac
}

# Docker Python installation
install_docker_python() {
    print_blue "Installing with Docker (Python/Flask)..."
    
    if [ "$GPU_SUPPORT" = true ]; then
        print_status "Using GPU-enabled configuration"
        docker-compose up -d background-removal-python redis
    else
        print_status "Using CPU-only configuration"
        docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d background-removal-python redis
    fi
    
    print_status "Application starting... Please wait for model download (first time only)"
    sleep 10
    
    # Wait for application to be ready
    wait_for_service "http://localhost:5000/api/health"
    
    echo ""
    print_status "🎉 Application is ready!"
    echo "Open your browser and go to: http://localhost:5000"
}

# Docker Node.js installation
install_docker_nodejs() {
    print_blue "Installing with Docker (Node.js/Express)..."
    
    docker-compose --profile nodejs up -d background-removal-nodejs
    
    # Wait for application to be ready
    wait_for_service "http://localhost:3000/api/health"
    
    echo ""
    print_status "🎉 Application is ready!"
    echo "Open your browser and go to: http://localhost:3000"
}

# Manual Python installation
install_manual_python() {
    print_blue "Manual Python installation..."
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required but not installed."
        exit 1
    fi
    
    # Create virtual environment
    print_status "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    
    # Install dependencies
    print_status "Installing Python dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    
    print_status "Starting Flask application..."
    export FLASK_APP=app.py
    export FLASK_ENV=development
    python app.py &
    
    # Wait for application to be ready
    wait_for_service "http://localhost:5000/api/health"
    
    echo ""
    print_status "🎉 Application is ready!"
    echo "Open your browser and go to: http://localhost:5000"
    echo "To stop the application, press Ctrl+C"
}

# Manual Node.js installation
install_manual_nodejs() {
    print_blue "Manual Node.js installation..."
    
    if ! command -v node &> /dev/null; then
        print_error "Node.js is required but not installed."
        exit 1
    fi
    
    # Install dependencies
    print_status "Installing Node.js dependencies..."
    npm install
    
    print_status "Starting Node.js application..."
    npm start &
    
    # Wait for application to be ready
    wait_for_service "http://localhost:3000/api/health"
    
    echo ""
    print_status "🎉 Application is ready!"
    echo "Open your browser and go to: http://localhost:3000"
    echo "To stop the application, press Ctrl+C"
}

# Development setup
install_development() {
    print_blue "Setting up development environment..."
    
    # Start with development configuration
    docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d
    
    print_status "Development environment starting..."
    print_status "- Python app: http://localhost:5000 (with hot reload)"
    print_status "- Redis: localhost:6379"
    
    # Wait for services
    wait_for_service "http://localhost:5000/api/health"
    
    echo ""
    print_status "🎉 Development environment is ready!"
    echo "You can now edit the code and see changes automatically."
}

# Wait for service to be ready
wait_for_service() {
    local url=$1
    local max_attempts=30
    local attempt=1
    
    print_status "Waiting for service to be ready at $url..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" > /dev/null 2>&1; then
            print_status "Service is ready!"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "Service failed to start within expected time"
    return 1
}

# Check if Remove.bg API key is configured
check_api_configuration() {
    if grep -q "your-remove-bg-api-key-here" .env; then
        echo ""
        print_warning "🔑 Optional: Configure Remove.bg API for premium results"
        echo "1. Sign up at https://www.remove.bg/api"
        echo "2. Get your API key"
        echo "3. Edit .env file and set REMOVE_BG_API_KEY=your-actual-key"
        echo "4. Set ENABLE_REMOVE_BG_FALLBACK=true"
    fi
}

# Main execution
main() {
    echo ""
    check_os
    check_prerequisites
    setup_environment
    choose_installation
    check_api_configuration
    
    echo ""
    echo "=================================================="
    print_status "🎨 Setup completed successfully!"
    echo ""
    print_status "Next steps:"
    echo "1. Open the application in your browser"
    echo "2. Upload an image to test background removal"
    echo "3. Check the README.md for advanced configuration"
    echo ""
    print_status "Useful commands:"
    echo "- View logs: docker-compose logs -f"
    echo "- Stop services: docker-compose down"
    echo "- Update application: git pull && docker-compose up --build"
    echo ""
    print_status "Need help? Check the documentation or open an issue on GitHub"
    echo "=================================================="
}

# Run main function
main "$@"