#!/usr/bin/env python3
"""
Test script to verify the background removal setup is working correctly.

This script checks:
1. All required packages are installed
2. Models can be loaded
3. Basic functionality works
4. GPU availability

Run this script before starting the main application to ensure everything is properly configured.
"""

import sys
import importlib
import subprocess
from pathlib import Path

def check_package(package_name, import_name=None):
    """Check if a package is installed and can be imported"""
    if import_name is None:
        import_name = package_name
    
    try:
        importlib.import_module(import_name)
        print(f"✅ {package_name}: OK")
        return True
    except ImportError:
        print(f"❌ {package_name}: MISSING")
        return False

def check_gpu():
    """Check GPU availability"""
    try:
        import torch
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            gpu_name = torch.cuda.get_device_name(0) if gpu_count > 0 else "Unknown"
            print(f"✅ GPU: {gpu_count} GPU(s) available - {gpu_name}")
            print(f"   CUDA Version: {torch.version.cuda}")
            return True
        else:
            print("⚠️  GPU: CUDA not available, will use CPU (slower)")
            return False
    except Exception as e:
        print(f"❌ GPU check failed: {e}")
        return False

def check_model_access():
    """Check if models can be accessed from HuggingFace"""
    try:
        import torch
        from transformers import AutoModelForImageSegmentation
        
        print("🔍 Testing model access...")
        
        # Test RMBG 2.0 access
        try:
            model = AutoModelForImageSegmentation.from_pretrained(
                'briaai/RMBG-2.0', 
                trust_remote_code=True,
                torch_dtype=torch.float32
            )
            print("✅ RMBG 2.0: Accessible")
            del model
        except Exception as e:
            print(f"⚠️  RMBG 2.0: Not accessible ({e})")
        
        # Test BiRefNet access
        try:
            model = AutoModelForImageSegmentation.from_pretrained(
                'ZhengPeng7/BiRefNet',
                trust_remote_code=True,
                torch_dtype=torch.float32
            )
            print("✅ BiRefNet: Accessible")
            del model
        except Exception as e:
            print(f"⚠️  BiRefNet: Not accessible ({e})")
            
        return True
    except Exception as e:
        print(f"❌ Model access test failed: {e}")
        return False

def check_file_structure():
    """Check if all required files are present"""
    required_files = [
        "app.py",
        "requirements.txt",
        "templates/index.html",
        "static/style.css",
        "README.md"
    ]
    
    print("📁 Checking file structure...")
    all_present = True
    
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}: Present")
        else:
            print(f"❌ {file_path}: Missing")
            all_present = False
    
    return all_present

def test_basic_functionality():
    """Test basic image processing functionality"""
    try:
        from PIL import Image, ImageDraw
        import numpy as np
        import cv2
        
        print("🧪 Testing basic functionality...")
        
        # Create a test image
        img = Image.new('RGB', (100, 100), 'white')
        draw = ImageDraw.Draw(img)
        draw.rectangle([25, 25, 75, 75], fill='blue')
        
        # Test PIL operations
        img_array = np.array(img)
        print("✅ PIL operations: OK")
        
        # Test OpenCV operations
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        print("✅ OpenCV operations: OK")
        
        # Test torch operations
        import torch
        tensor = torch.from_numpy(img_array).float()
        print("✅ PyTorch operations: OK")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Background Removal Setup Test")
    print("=" * 50)
    
    # Check Python version
    python_version = sys.version_info
    print(f"🐍 Python Version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        print("⚠️  Warning: Python 3.8 or higher recommended")
    
    print("\n📦 Checking Required Packages:")
    packages_ok = True
    
    # Core packages
    required_packages = [
        ("Flask", "flask"),
        ("PyTorch", "torch"),
        ("torchvision", "torchvision"),
        ("Transformers", "transformers"),
        ("Pillow", "PIL"),
        ("NumPy", "numpy"),
        ("OpenCV", "cv2"),
        ("Kornia", "kornia"),
        ("Flask-CORS", "flask_cors")
    ]
    
    for package_name, import_name in required_packages:
        if not check_package(package_name, import_name):
            packages_ok = False
    
    if not packages_ok:
        print("\n❌ Some packages are missing. Install them with:")
        print("   pip install -r requirements.txt")
        return False
    
    print("\n💻 Checking Hardware:")
    gpu_available = check_gpu()
    
    print("\n📁 Checking Files:")
    files_ok = check_file_structure()
    
    if not files_ok:
        print("\n❌ Some required files are missing.")
        return False
    
    print("\n🧪 Testing Functionality:")
    functionality_ok = test_basic_functionality()
    
    if not functionality_ok:
        return False
    
    print("\n🌐 Testing Model Access:")
    model_access_ok = check_model_access()
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 SETUP TEST SUMMARY")
    print("=" * 50)
    
    checks = [
        ("Required Packages", packages_ok),
        ("File Structure", files_ok),
        ("Basic Functionality", functionality_ok),
        ("GPU Availability", gpu_available),
        ("Model Access", model_access_ok)
    ]
    
    all_passed = True
    for check_name, passed in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{check_name:<20}: {status}")
        if not passed and check_name in ["Required Packages", "File Structure", "Basic Functionality"]:
            all_passed = False
    
    print("\n" + "=" * 50)
    
    if all_passed:
        print("🎉 SETUP TEST PASSED!")
        print("You can now run the application with: python app.py")
        
        if not gpu_available:
            print("\n⚠️  Note: Running on CPU will be slower than GPU")
        
        if not model_access_ok:
            print("\n⚠️  Note: Some models may not be accessible")
            print("   Check internet connection and HuggingFace access")
        
    else:
        print("❌ SETUP TEST FAILED!")
        print("Please fix the issues above before running the application")
        
        print("\n💡 Common fixes:")
        print("   - Install missing packages: pip install -r requirements.txt")
        print("   - Ensure all files are present")
        print("   - Check Python version (3.8+ recommended)")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)