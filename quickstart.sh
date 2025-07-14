#!/bin/bash

# AI Background Removal Tool - Quick Start Script
# This script provides one-command setup for the background removal application

set -e  # Exit on any error

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

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check system requirements
check_requirements() {
    print_status "Checking system requirements..."
    
    # Check Python
    if command_exists python3; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        print_success "Python $PYTHON_VERSION found"
    else
        print_error "Python 3 is required but not found"
        exit 1
    fi
    
    # Check pip
    if command_exists pip3; then
        print_success "pip3 found"
    else
        print_error "pip3 is required but not found"
        exit 1
    fi
    
    # Check Docker (optional)
    if command_exists docker; then
        print_success "Docker found"
        DOCKER_AVAILABLE=true
    else
        print_warning "Docker not found - Docker deployment won't be available"
        DOCKER_AVAILABLE=false
    fi
    
    # Check available disk space
    AVAILABLE_SPACE=$(df . | tail -1 | awk '{print $4}')
    if [ "$AVAILABLE_SPACE" -lt 2000000 ]; then  # Less than 2GB
        print_warning "Low disk space detected. At least 2GB recommended for AI models"
    fi
}

# Function to setup Python environment
setup_python_env() {
    print_status "Setting up Python environment..."
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_success "Virtual environment created"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install requirements
    if [ -f "requirements.txt" ]; then
        print_status "Installing Python dependencies..."
        pip install -r requirements.txt
        print_success "Dependencies installed"
    else
        print_error "requirements.txt not found"
        exit 1
    fi
}

# Function to download AI models
download_models() {
    print_status "Downloading AI models (this may take a few minutes)..."
    
    python3 -c "
import sys
try:
    from rembg import new_session
    print('Downloading U2-Net model...')
    new_session('u2net')
    print('Downloading IS-Net model...')
    new_session('isnet-general-use')
    print('✅ Models downloaded successfully')
except Exception as e:
    print(f'⚠️  Models will be downloaded on first use: {e}')
    sys.exit(0)
"
}

# Function to run tests
run_tests() {
    print_status "Running basic tests..."
    
    python3 -c "
import sys
try:
    from PIL import Image
    import numpy as np
    import cv2
    import torch
    
    # Test basic functionality
    test_image = Image.new('RGB', (100, 100), color='red')
    test_array = np.array(test_image)
    
    print('✅ Basic image processing works')
    print(f'✅ PyTorch device: {torch.device(\"cuda\" if torch.cuda.is_available() else \"cpu\")}')
    
except ImportError as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
except Exception as e:
    print(f'❌ Test failed: {e}')
    sys.exit(1)
"
}

# Function to start the application
start_application() {
    print_status "Starting the application..."
    
    # Check if port 5000 is available
    if lsof -Pi :5000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "Port 5000 is already in use"
        read -p "Do you want to kill the existing process? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            kill $(lsof -t -i:5000) 2>/dev/null || true
            sleep 2
        else
            print_error "Cannot start - port 5000 is in use"
            exit 1
        fi
    fi
    
    # Start the application
    print_success "Application starting on http://localhost:5000"
    print_status "Press Ctrl+C to stop the application"
    
    # Activate virtual environment if it exists
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    python3 app.py
}

# Function for Docker deployment
docker_deploy() {
    if [ "$DOCKER_AVAILABLE" = false ]; then
        print_error "Docker is not available"
        exit 1
    fi
    
    print_status "Building Docker image..."
    docker build -t ai-background-removal .
    
    print_status "Starting Docker container..."
    docker run -d \
        --name bg-removal-app \
        -p 5000:5000 \
        -v $(pwd)/uploads:/app/uploads \
        -v $(pwd)/processed:/app/processed \
        ai-background-removal
    
    print_success "Docker container started"
    print_status "Application available at http://localhost:5000"
    print_status "To stop: docker stop bg-removal-app"
}

# Function for Docker Compose deployment
docker_compose_deploy() {
    if [ "$DOCKER_AVAILABLE" = false ]; then
        print_error "Docker is not available"
        exit 1
    fi
    
    if ! command_exists docker-compose; then
        print_error "docker-compose is not available"
        exit 1
    fi
    
    print_status "Starting full stack with Docker Compose..."
    docker-compose up -d
    
    print_success "Full stack deployed"
    print_status "Application: http://localhost:5000"
    print_status "Monitoring: http://localhost:3000 (admin/admin123)"
    print_status "To stop: docker-compose down"
}

# Function to show usage
show_usage() {
    echo "AI Background Removal Tool - Quick Start"
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  setup     Set up the development environment"
    echo "  start     Start the application (development mode)"
    echo "  docker    Deploy using Docker"
    echo "  compose   Deploy full stack using Docker Compose"
    echo "  test      Run tests only"
    echo "  clean     Clean up generated files"
    echo "  help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 setup     # Set up and start in development mode"
    echo "  $0 docker    # Deploy using Docker"
    echo "  $0 compose   # Deploy full stack with monitoring"
}

# Function to clean up
cleanup() {
    print_status "Cleaning up..."
    
    # Remove virtual environment
    if [ -d "venv" ]; then
        rm -rf venv
        print_success "Virtual environment removed"
    fi
    
    # Remove uploaded and processed files
    rm -rf uploads/* processed/* 2>/dev/null || true
    
    # Remove Docker containers and images
    if [ "$DOCKER_AVAILABLE" = true ]; then
        docker stop bg-removal-app 2>/dev/null || true
        docker rm bg-removal-app 2>/dev/null || true
        docker-compose down 2>/dev/null || true
    fi
    
    print_success "Cleanup completed"
}

# Main execution
main() {
    echo "🎨 AI Background Removal Tool - Quick Start"
    echo "============================================"
    
    # Check requirements first
    check_requirements
    
    case "${1:-setup}" in
        "setup"|"")
            setup_python_env
            download_models
            run_tests
            print_success "Setup completed successfully!"
            echo ""
            read -p "Start the application now? (Y/n): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Nn]$ ]]; then
                print_status "To start later, run: $0 start"
            else
                start_application
            fi
            ;;
        "start")
            start_application
            ;;
        "docker")
            docker_deploy
            ;;
        "compose")
            docker_compose_deploy
            ;;
        "test")
            if [ -d "venv" ]; then
                source venv/bin/activate
            fi
            run_tests
            ;;
        "clean")
            cleanup
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
}

# Handle Ctrl+C gracefully
trap 'echo -e "\n${YELLOW}[INFO]${NC} Script interrupted by user"; exit 130' INT

# Run main function
main "$@"