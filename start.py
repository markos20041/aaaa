#!/usr/bin/env python3
"""
AI Background Remover - Startup Script
This script checks dependencies and launches the background removal tool.
"""

import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required. Current version:", sys.version)
        return False
    print("✅ Python version:", sys.version.split()[0])
    return True

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = [
        'flask', 'flask-cors', 'rembg', 'pillow', 
        'numpy', 'opencv-python', 'torch', 'scikit-image'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package}")
            missing_packages.append(package)
    
    return missing_packages

def install_dependencies(packages):
    """Install missing packages"""
    print(f"\n🔧 Installing {len(packages)} missing packages...")
    try:
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', 
            '--upgrade', 'pip'
        ])
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install'
        ] + packages)
        print("✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def start_backend():
    """Start the Flask backend server"""
    print("\n🚀 Starting backend server...")
    try:
        # Start Flask app in background
        process = subprocess.Popen([
            sys.executable, 'app.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a bit for server to start
        time.sleep(3)
        
        # Check if process is still running
        if process.poll() is None:
            print("✅ Backend server started on http://localhost:5000")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"❌ Backend failed to start:")
            print(f"STDOUT: {stdout.decode()}")
            print(f"STDERR: {stderr.decode()}")
            return None
            
    except Exception as e:
        print(f"❌ Failed to start backend: {e}")
        return None

def open_frontend():
    """Open the frontend in default web browser"""
    frontend_path = Path('index.html').absolute()
    
    if frontend_path.exists():
        print(f"\n🌐 Opening frontend: {frontend_path}")
        webbrowser.open(f'file://{frontend_path}')
        return True
    else:
        print(f"❌ Frontend file not found: {frontend_path}")
        return False

def print_instructions():
    """Print usage instructions"""
    print("""
🎉 AI Background Remover is ready!

📖 How to use:
1. Upload an image (PNG, JPG, JPEG, WEBP)
2. Choose your AI model and settings
3. Click "Remove Background"
4. Download your result or fine-tune with editing tools

🔧 Available models:
- U-2-Net: Best overall performance
- U-2-Net Human: Optimized for people
- Silueta: Fast processing
- ISNet: Highest quality (slower)

🛠️ Advanced features:
- Edge enhancement for better hair/detail preservation
- Alpha matting for professional edge quality
- Manual editing with brush tools
- Drag & drop file upload

❓ Need help? Check the README.md file for detailed documentation.

Press Ctrl+C to stop the server.
""")

def main():
    """Main startup function"""
    print("🎨 AI Background Remover - Professional Tool")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Check dependencies
    print("\n📦 Checking dependencies...")
    missing = check_dependencies()
    
    if missing:
        print(f"\n⚠️  Missing {len(missing)} required packages")
        install = input("Install missing packages? (y/n): ").lower().strip()
        
        if install == 'y':
            if not install_dependencies(missing):
                print("\n❌ Failed to install dependencies. Please install manually:")
                print(f"pip install {' '.join(missing)}")
                sys.exit(1)
        else:
            print("❌ Cannot proceed without required packages")
            sys.exit(1)
    
    print("✅ All dependencies satisfied!")
    
    # Start backend
    backend_process = start_backend()
    if not backend_process:
        print("❌ Failed to start backend server")
        sys.exit(1)
    
    # Open frontend
    if open_frontend():
        print_instructions()
        
        try:
            # Keep the script running
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n🛑 Shutting down...")
            backend_process.terminate()
            backend_process.wait()
            print("✅ Server stopped. Goodbye!")
    else:
        backend_process.terminate()
        print("❌ Failed to open frontend")
        sys.exit(1)

if __name__ == "__main__":
    main()