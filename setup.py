#!/usr/bin/env python3
"""
AI Background Removal Tool Setup Script
This script helps you set up and run the background removal application.
"""

import subprocess
import sys
import os
import platform

def install_requirements():
    """Install Python requirements"""
    print("📦 Installing Python requirements...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Requirements installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install requirements: {e}")
        return False

def create_directories():
    """Create necessary directories"""
    directories = ['uploads', 'processed', 'static', 'templates']
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"📁 Created directory: {directory}")

def check_system_dependencies():
    """Check for system dependencies"""
    print("🔍 Checking system dependencies...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        return False
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    # Check for CUDA (optional)
    try:
        import torch
        if torch.cuda.is_available():
            print(f"✅ CUDA available: {torch.cuda.get_device_name(0)}")
        else:
            print("⚠️  CUDA not available, using CPU (slower processing)")
    except ImportError:
        print("⚠️  PyTorch not installed yet")
    
    return True

def download_models():
    """Download AI models"""
    print("🤖 Downloading AI models...")
    try:
        # This will download models on first use
        from rembg import new_session
        models = ['u2net', 'isnet-general-use']
        
        for model in models:
            print(f"📥 Downloading {model} model...")
            session = new_session(model)
            print(f"✅ {model} model ready")
        
        return True
    except Exception as e:
        print(f"⚠️  Model download will happen on first use: {e}")
        return True

def run_tests():
    """Run basic tests"""
    print("🧪 Running basic tests...")
    try:
        from PIL import Image
        import numpy as np
        import cv2
        
        # Create a test image
        test_image = Image.new('RGB', (100, 100), color='red')
        test_array = np.array(test_image)
        
        print("✅ Basic image processing works")
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🎨 AI Background Removal Tool Setup")
    print("=" * 40)
    
    # Check system requirements
    if not check_system_dependencies():
        print("❌ System requirements not met")
        return False
    
    # Create directories
    create_directories()
    
    # Install requirements
    if not install_requirements():
        print("❌ Failed to install requirements")
        return False
    
    # Download models
    download_models()
    
    # Run tests
    if not run_tests():
        print("❌ Tests failed")
        return False
    
    print("\n🎉 Setup completed successfully!")
    print("\n🚀 To start the application, run:")
    print("   python app.py")
    print("\n🌐 Then open: http://localhost:5000")
    
    # Ask if user wants to start the app
    try:
        start_now = input("\n❓ Start the application now? (y/N): ").lower().strip()
        if start_now in ['y', 'yes']:
            print("\n🚀 Starting application...")
            subprocess.run([sys.executable, "app.py"])
    except KeyboardInterrupt:
        print("\n👋 Setup completed. Run 'python app.py' when you're ready!")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)