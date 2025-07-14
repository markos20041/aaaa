#!/bin/bash

# AI Background Removal Tool - Deployment Script
# This script sets up and deploys the background removal application

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="bg-removal-tool"
DOCKER_IMAGE_NAME="bg-removal-app"
DEFAULT_PORT=8000
DEFAULT_DEVICE="auto"  # auto, cpu, cuda

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Parse command line arguments
DEPLOYMENT_TYPE="docker"
DEVICE="auto"
PORT=$DEFAULT_PORT
GPU_SUPPORT=false
PRODUCTION=false

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -t, --type TYPE         Deployment type (docker|local) [default: docker]"
    echo "  -d, --device DEVICE     Device type (auto|cpu|cuda) [default: auto]"
    echo "  -p, --port PORT         Port number [default: 8000]"
    echo "  -g, --gpu              Enable GPU support"
    echo "  --production           Production deployment with optimizations"
    echo "  -h, --help             Show this help message"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            DEPLOYMENT_TYPE="$2"
            shift 2
            ;;
        -d|--device)
            DEVICE="$2"
            shift 2
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -g|--gpu)
            GPU_SUPPORT=true
            shift
            ;;
        --production)
            PRODUCTION=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            ;;
    esac
done

# Detect system capabilities
detect_system() {
    log_info "Detecting system capabilities..."
    
    # Check if NVIDIA GPU is available
    if command -v nvidia-smi &> /dev/null; then
        if nvidia-smi &> /dev/null; then
            log_success "NVIDIA GPU detected"
            if [[ "$DEVICE" == "auto" ]]; then
                DEVICE="cuda"
                GPU_SUPPORT=true
            fi
        else
            log_warning "NVIDIA driver not properly installed"
        fi
    else
        log_info "No NVIDIA GPU detected"
        if [[ "$DEVICE" == "auto" ]]; then
            DEVICE="cpu"
        fi
    fi
    
    # Check Docker
    if command -v docker &> /dev/null; then
        log_success "Docker is available"
    else
        log_error "Docker is required but not installed"
        exit 1
    fi
    
    # Check Docker Compose
    if command -v docker-compose &> /dev/null; then
        log_success "Docker Compose is available"
    else
        log_error "Docker Compose is required but not installed"
        exit 1
    fi
}

# Setup directories
setup_directories() {
    log_info "Setting up directories..."
    
    mkdir -p models
    mkdir -p temp
    mkdir -p logs
    mkdir -p static
    mkdir -p templates
    
    # Set permissions
    chmod 755 models temp logs
    
    log_success "Directories created"
}

# Check and install requirements
check_requirements() {
    log_info "Checking requirements..."
    
    # Check Python version for local deployment
    if [[ "$DEPLOYMENT_TYPE" == "local" ]]; then
        if command -v python3 &> /dev/null; then
            PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
            if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 9) else 1)'; then
                log_success "Python $PYTHON_VERSION is compatible"
            else
                log_error "Python 3.9+ is required, found $PYTHON_VERSION"
                exit 1
            fi
        else
            log_error "Python 3 is required but not found"
            exit 1
        fi
    fi
    
    # Check available memory
    TOTAL_MEM=$(free -g | awk '/^Mem:/{print $2}')
    if [[ $TOTAL_MEM -lt 4 ]]; then
        log_warning "Low memory detected: ${TOTAL_MEM}GB. Recommended: 8GB+"
    else
        log_success "Memory check passed: ${TOTAL_MEM}GB"
    fi
}

# Download models
download_models() {
    log_info "Checking models..."
    
    if [[ ! -f "models/model_downloaded.flag" ]]; then
        log_info "Models will be downloaded automatically on first run"
        log_warning "First startup may take 5-10 minutes to download models"
    else
        log_success "Models already available"
    fi
}

# Local deployment
deploy_local() {
    log_info "Starting local deployment..."
    
    # Create virtual environment if it doesn't exist
    if [[ ! -d "venv" ]]; then
        log_info "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install dependencies
    log_info "Installing dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Set environment variables
    export DEVICE=$DEVICE
    export MODEL_CACHE_DIR="./models"
    export TEMP_DIR="./temp"
    export LOG_LEVEL="INFO"
    
    if [[ "$PRODUCTION" == true ]]; then
        export LOG_LEVEL="WARNING"
        log_info "Starting in production mode..."
        uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1 --access-log
    else
        log_info "Starting in development mode..."
        uvicorn app.main:app --host 0.0.0.0 --port $PORT --reload
    fi
}

# Docker deployment
deploy_docker() {
    log_info "Starting Docker deployment..."
    
    # Create environment file
    cat > .env << EOF
DEVICE=$DEVICE
MODEL_CACHE_DIR=/app/models
TEMP_DIR=/app/temp
LOG_LEVEL=INFO
MAX_WORKERS=1
EOF
    
    # Modify docker-compose.yml for GPU support
    if [[ "$GPU_SUPPORT" == true ]]; then
        log_info "Enabling GPU support in Docker Compose..."
        
        # Create GPU-enabled docker-compose file
        cp docker-compose.yml docker-compose.gpu.yml
        
        # Uncomment GPU section in docker-compose file
        sed -i 's/# deploy:/deploy:/' docker-compose.gpu.yml
        sed -i 's/#   resources:/  resources:/' docker-compose.gpu.yml
        sed -i 's/#     reservations:/    reservations:/' docker-compose.gpu.yml
        sed -i 's/#       devices:/      devices:/' docker-compose.gpu.yml
        sed -i 's/#         - driver: nvidia/        - driver: nvidia/' docker-compose.gpu.yml
        sed -i 's/#           count: 1/          count: 1/' docker-compose.gpu.yml
        sed -i 's/#           capabilities: \[gpu\]/          capabilities: [gpu]/' docker-compose.gpu.yml
        
        COMPOSE_FILE="docker-compose.gpu.yml"
    else
        COMPOSE_FILE="docker-compose.yml"
    fi
    
    # Update port in docker-compose
    sed -i "s/8000:8000/$PORT:8000/" $COMPOSE_FILE
    
    # Build and start
    log_info "Building Docker image..."
    docker-compose -f $COMPOSE_FILE build
    
    log_info "Starting services..."
    docker-compose -f $COMPOSE_FILE up -d
    
    # Wait for service to be ready
    log_info "Waiting for service to be ready..."
    for i in {1..30}; do
        if curl -f http://localhost:$PORT/health &> /dev/null; then
            break
        fi
        sleep 2
    done
}

# Health check
health_check() {
    log_info "Performing health check..."
    
    if curl -f http://localhost:$PORT/health &> /dev/null; then
        log_success "Service is healthy!"
        
        # Get service info
        RESPONSE=$(curl -s http://localhost:$PORT/health)
        echo "Service details:"
        echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    else
        log_error "Service health check failed"
        exit 1
    fi
}

# Cleanup function
cleanup() {
    if [[ "$DEPLOYMENT_TYPE" == "docker" ]]; then
        log_info "To stop the service, run: docker-compose down"
        log_info "To view logs, run: docker-compose logs -f"
    fi
}

# Performance tips
show_performance_tips() {
    log_info "Performance Tips:"
    echo "  • Use GPU deployment for best performance"
    echo "  • Allocate at least 8GB RAM for optimal performance"
    echo "  • Use batch processing for multiple images"
    echo "  • Monitor memory usage during high load"
    
    if [[ "$DEVICE" == "cpu" ]]; then
        log_warning "CPU-only deployment detected. Consider GPU for better performance."
    fi
}

# Main deployment function
main() {
    echo "============================================"
    echo "  AI Background Removal Tool - Deployment  "
    echo "============================================"
    echo ""
    
    log_info "Configuration:"
    echo "  Deployment Type: $DEPLOYMENT_TYPE"
    echo "  Device: $DEVICE"
    echo "  Port: $PORT"
    echo "  GPU Support: $GPU_SUPPORT"
    echo "  Production Mode: $PRODUCTION"
    echo ""
    
    detect_system
    setup_directories
    check_requirements
    download_models
    
    if [[ "$DEPLOYMENT_TYPE" == "local" ]]; then
        deploy_local
    elif [[ "$DEPLOYMENT_TYPE" == "docker" ]]; then
        deploy_docker
        sleep 5  # Give services time to start
        health_check
        cleanup
    else
        log_error "Invalid deployment type: $DEPLOYMENT_TYPE"
        exit 1
    fi
    
    echo ""
    log_success "Deployment completed successfully!"
    echo ""
    echo "🎉 Your AI Background Removal Tool is ready!"
    echo "🌐 Access the web interface: http://localhost:$PORT"
    echo "📚 API Documentation: http://localhost:$PORT/docs"
    echo ""
    
    show_performance_tips
}

# Run main function
main "$@"