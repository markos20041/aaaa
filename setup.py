#!/usr/bin/env python3
"""
Background Removal Tool Setup Script
Installs dependencies, downloads models, and sets up the environment
"""

import os
import sys
import subprocess
import platform
import urllib.request
import shutil
from pathlib import Path

def run_command(command, check=True):
    """Run shell command and handle errors"""
    print(f"Running: {command}")
    try:
        result = subprocess.run(command, shell=True, check=check, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print("❌ Python 3.9 or higher is required")
        print(f"Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✅ Python version {version.major}.{version.minor}.{version.micro} is compatible")
    return True

def check_system_requirements():
    """Check system requirements"""
    print("🔍 Checking system requirements...")
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Check available disk space (at least 2GB for models)
    try:
        statvfs = os.statvfs('.')
        free_space = statvfs.f_bavail * statvfs.f_frsize / (1024**3)  # GB
        if free_space < 2:
            print(f"❌ Insufficient disk space. Need at least 2GB, have {free_space:.1f}GB")
            return False
        print(f"✅ Sufficient disk space: {free_space:.1f}GB available")
    except:
        print("⚠️  Could not check disk space")
    
    return True

def setup_virtual_environment():
    """Create and activate virtual environment"""
    print("🔧 Setting up virtual environment...")
    
    venv_path = Path("venv")
    
    if venv_path.exists():
        print("Virtual environment already exists")
        return True
    
    # Create virtual environment
    if not run_command(f"{sys.executable} -m venv venv"):
        print("❌ Failed to create virtual environment")
        return False
    
    print("✅ Virtual environment created")
    return True

def install_dependencies():
    """Install Python dependencies"""
    print("📦 Installing Python dependencies...")
    
    # Determine pip command based on OS
    if platform.system() == "Windows":
        pip_cmd = "venv\\Scripts\\pip"
        python_cmd = "venv\\Scripts\\python"
    else:
        pip_cmd = "venv/bin/pip"
        python_cmd = "venv/bin/python"
    
    # Upgrade pip first
    if not run_command(f"{pip_cmd} install --upgrade pip"):
        print("❌ Failed to upgrade pip")
        return False
    
    # Install PyTorch (CPU version for compatibility, can be upgraded to GPU later)
    print("Installing PyTorch...")
    torch_command = f"{pip_cmd} install torch torchvision --index-url https://download.pytorch.org/whl/cpu"
    if not run_command(torch_command):
        print("❌ Failed to install PyTorch")
        return False
    
    # Install other dependencies
    if not run_command(f"{pip_cmd} install -r requirements.txt"):
        print("❌ Failed to install dependencies")
        return False
    
    print("✅ Dependencies installed successfully")
    return True

def download_models():
    """Pre-download models to avoid first-run delays"""
    print("🤖 Pre-downloading AI models...")
    
    # Determine python command
    if platform.system() == "Windows":
        python_cmd = "venv\\Scripts\\python"
    else:
        python_cmd = "venv/bin/python"
    
    # Create model download script
    download_script = """
import torch
from transformers import AutoModelForImageSegmentation, AutoProcessor
from rembg import new_session
import os

print("Downloading RMBG-1.4 model...")
try:
    model = AutoModelForImageSegmentation.from_pretrained('briaai/RMBG-1.4', trust_remote_code=True)
    processor = AutoProcessor.from_pretrained('briaai/RMBG-1.4', trust_remote_code=True)
    print("✅ RMBG-1.4 model downloaded")
except Exception as e:
    print(f"⚠️  Could not download RMBG-1.4: {e}")

print("Downloading U2Net model...")
try:
    session = new_session('u2net')
    print("✅ U2Net model downloaded")
except Exception as e:
    print(f"⚠️  Could not download U2Net: {e}")

print("Model download complete!")
"""
    
    with open("download_models.py", "w") as f:
        f.write(download_script)
    
    # Run the download script
    success = run_command(f"{python_cmd} download_models.py")
    
    # Clean up
    os.remove("download_models.py")
    
    if success:
        print("✅ Models downloaded successfully")
    else:
        print("⚠️  Some models may not have downloaded. They will be downloaded on first use.")
    
    return True

def create_startup_scripts():
    """Create startup scripts for different platforms"""
    print("📝 Creating startup scripts...")
    
    # Windows batch script
    windows_script = """@echo off
echo Starting Background Removal Server...
cd /d "%~dp0"
call venv\\Scripts\\activate
python app.py
pause
"""
    
    with open("start_server.bat", "w") as f:
        f.write(windows_script)
    
    # Unix shell script
    unix_script = """#!/bin/bash
echo "Starting Background Removal Server..."
cd "$(dirname "$0")"
source venv/bin/activate
python app.py
"""
    
    with open("start_server.sh", "w") as f:
        f.write(unix_script)
    
    # Make shell script executable
    if platform.system() != "Windows":
        os.chmod("start_server.sh", 0o755)
    
    print("✅ Startup scripts created")
    return True

def create_docker_files():
    """Create Docker configuration files"""
    print("🐳 Creating Docker configuration...")
    
    dockerfile = """FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    libgl1-mesa-glx \\
    libglib2.0-0 \\
    libsm6 \\
    libxext6 \\
    libxrender-dev \\
    libgomp1 \\
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for temporary files
RUN mkdir -p temp_uploads temp_results

# Expose port
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "app:app"]
"""
    
    with open("Dockerfile", "w") as f:
        f.write(dockerfile)
    
    # Docker Compose file
    docker_compose = """version: '3.8'

services:
  background-removal:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./temp_uploads:/app/temp_uploads
      - ./temp_results:/app/temp_results
    environment:
      - FLASK_ENV=production
    restart: unless-stopped
    
  # Optional: Redis for caching
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    restart: unless-stopped

  # Optional: Nginx for serving static files
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - .:/usr/share/nginx/html
    depends_on:
      - background-removal
    restart: unless-stopped
"""
    
    with open("docker-compose.yml", "w") as f:
        f.write(docker_compose)
    
    print("✅ Docker files created")
    return True

def create_readme():
    """Create comprehensive README file"""
    print("📖 Creating README...")
    
    readme_content = """# AI Background Removal Tool

A high-performance web application for automatic background removal using state-of-the-art AI models.

## Features

- 🤖 **AI-Powered**: Uses RMBG-1.4 and U2Net models for superior accuracy
- 🎨 **Edge Enhancement**: Advanced algorithms for hair and fine detail preservation
- 🔧 **Customizable**: Adjustable feathering, edge enhancement options
- 📱 **Responsive**: Works on desktop, tablet, and mobile devices
- ⚡ **Fast**: Optimized processing pipeline with GPU acceleration
- 🌐 **Multi-language**: Arabic interface with RTL support

## Quick Start

### Option 1: Automatic Setup
```bash
python setup.py
```

### Option 2: Manual Setup
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows)
venv\\Scripts\\activate
# Or on Linux/Mac
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the server
python app.py
```

### Option 3: Docker
```bash
docker-compose up --build
```

## Usage

1. **Start the server** using one of the methods above
2. **Open your browser** to `http://localhost:5000`
3. **Upload an image** (PNG, JPG, WebP up to 16MB)
4. **Adjust settings** if needed (method, edge feathering, etc.)
5. **Process** and download your result!

## API Usage

### Remove Background
```bash
curl -X POST \\
  http://localhost:5000/api/remove-background \\
  -F "image=@your_image.jpg" \\
  -F "method=auto" \\
  -F "feather_radius=2" \\
  -F "enhance_edges=true"
```

### Download Result
```bash
curl -o result.png http://localhost:5000/api/download/{result_id}
```

## Performance Optimization

### For Production:
1. **Use GPU**: Install CUDA-enabled PyTorch
2. **Enable Redis**: Uncomment Redis in docker-compose.yml
3. **Use Nginx**: For serving static files and load balancing
4. **Scale horizontally**: Add more worker containers

### GPU Setup:
```bash
# Install CUDA-enabled PyTorch
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

## Troubleshooting

### Common Issues:

1. **Out of Memory**: Reduce image size or use CPU-only mode
2. **Slow Processing**: Enable GPU acceleration or use faster models
3. **CORS Errors**: Check that backend is running on port 5000
4. **Model Download Fails**: Check internet connection and try again

### Performance Tips:

- Use RMBG model for best quality
- Use U2Net for faster processing
- Enable edge enhancement for portraits
- Adjust feather radius for different image types

## License

This project is licensed under the MIT License.

## Support

For issues and questions, please check the troubleshooting section or create an issue on GitHub.
"""
    
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    print("✅ README created")
    return True

def main():
    """Main setup function"""
    print("🚀 Background Removal Tool Setup")
    print("=" * 50)
    
    # Check system requirements
    if not check_system_requirements():
        print("❌ System requirements not met")
        return False
    
    # Create necessary directories
    os.makedirs("temp_uploads", exist_ok=True)
    os.makedirs("temp_results", exist_ok=True)
    
    # Setup steps
    steps = [
        ("Virtual Environment", setup_virtual_environment),
        ("Dependencies", install_dependencies),
        ("AI Models", download_models),
        ("Startup Scripts", create_startup_scripts),
        ("Docker Files", create_docker_files),
        ("Documentation", create_readme),
    ]
    
    for step_name, step_func in steps:
        print(f"\n🔄 {step_name}...")
        if not step_func():
            print(f"❌ Failed at step: {step_name}")
            return False
    
    print("\n" + "=" * 50)
    print("🎉 Setup completed successfully!")
    print("\nNext steps:")
    print("1. Activate the virtual environment:")
    if platform.system() == "Windows":
        print("   venv\\Scripts\\activate")
    else:
        print("   source venv/bin/activate")
    print("2. Start the server:")
    print("   python app.py")
    print("3. Open http://localhost:5000 in your browser")
    print("\nOr use the startup scripts:")
    if platform.system() == "Windows":
        print("   start_server.bat")
    else:
        print("   ./start_server.sh")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        sys.exit(1)