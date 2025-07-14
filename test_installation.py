#!/usr/bin/env python3
"""
Test script to verify the background removal tool installation
"""

import os
import sys
import requests
import time
import subprocess
import threading
from PIL import Image, ImageDraw
import io

def create_test_image():
    """Create a simple test image for background removal"""
    # Create a 300x300 image with a red circle on white background
    img = Image.new('RGB', (300, 300), 'white')
    draw = ImageDraw.Draw(img)
    
    # Draw a red circle in the center
    draw.ellipse([75, 75, 225, 225], fill='red', outline='darkred', width=3)
    
    # Add some text
    try:
        draw.text((120, 140), "TEST", fill='white')
    except:
        pass  # Font might not be available
    
    # Save to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    return img_bytes.getvalue()

def start_server():
    """Start the Flask server in a subprocess"""
    try:
        # Try to start the server
        process = subprocess.Popen([
            sys.executable, 'app.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a bit for server to start
        time.sleep(5)
        
        return process
    except Exception as e:
        print(f"Failed to start server: {e}")
        return None

def test_server_health():
    """Test if the server is responding"""
    try:
        response = requests.get('http://localhost:5000/api/health', timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Server is healthy")
            print(f"   - Status: {data.get('status')}")
            print(f"   - Device: {data.get('device')}")
            print(f"   - Models loaded: {data.get('models_loaded')}")
            return True
        else:
            print(f"❌ Server health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Could not connect to server: {e}")
        return False

def test_background_removal():
    """Test the background removal functionality"""
    try:
        print("🧪 Testing background removal...")
        
        # Create test image
        test_image = create_test_image()
        
        # Prepare the request
        files = {'image': ('test.png', test_image, 'image/png')}
        data = {
            'method': 'auto',
            'feather_radius': '2',
            'enhance_edges': 'true'
        }
        
        # Send the request
        response = requests.post(
            'http://localhost:5000/api/remove-background',
            files=files,
            data=data,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ Background removal successful")
                print(f"   - Result ID: {result.get('result_id')}")
                print(f"   - Download URL: {result.get('download_url')}")
                
                # Test download
                download_url = f"http://localhost:5000{result.get('download_url')}"
                download_response = requests.get(download_url, timeout=30)
                
                if download_response.status_code == 200:
                    print("✅ Result download successful")
                    print(f"   - File size: {len(download_response.content)} bytes")
                    
                    # Save test result
                    with open('test_result.png', 'wb') as f:
                        f.write(download_response.content)
                    print("   - Saved as test_result.png")
                    
                    return True
                else:
                    print(f"❌ Download failed: {download_response.status_code}")
                    return False
            else:
                print(f"❌ Processing failed: {result}")
                return False
        else:
            print(f"❌ Request failed: {response.status_code}")
            if response.headers.get('content-type') == 'application/json':
                print(f"   Error: {response.json()}")
            return False
            
    except Exception as e:
        print(f"❌ Background removal test failed: {e}")
        return False

def test_frontend():
    """Test if the frontend is accessible"""
    try:
        response = requests.get('http://localhost:5000/', timeout=10)
        if response.status_code == 200:
            print("✅ Frontend is accessible")
            if 'إزالة خلفية الصورة' in response.text:
                print("   - Background removal tool found in UI")
            return True
        else:
            print(f"❌ Frontend not accessible: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Could not access frontend: {e}")
        return False

def run_tests():
    """Run all tests"""
    print("🧪 Background Removal Tool - Installation Test")
    print("=" * 50)
    
    # Check if required files exist
    required_files = ['app.py', 'requirements.txt', 'index.html', 'script.js', 'style.css']
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        print(f"❌ Missing required files: {missing_files}")
        return False
    
    print("✅ All required files present")
    
    # Start the server
    print("\n🚀 Starting server...")
    server_process = start_server()
    
    if not server_process:
        print("❌ Could not start server")
        return False
    
    try:
        # Wait for server to be ready
        print("⏳ Waiting for server to be ready...")
        for i in range(10):
            if test_server_health():
                break
            time.sleep(2)
            print(f"   Attempt {i+1}/10...")
        else:
            print("❌ Server did not become ready")
            return False
        
        # Test frontend
        print("\n🌐 Testing frontend...")
        if not test_frontend():
            return False
        
        # Test background removal
        print("\n🎨 Testing background removal...")
        if not test_background_removal():
            return False
        
        print("\n" + "=" * 50)
        print("🎉 All tests passed!")
        print("\nYour background removal tool is working correctly!")
        print("\nNext steps:")
        print("1. Open http://localhost:5000 in your browser")
        print("2. Try uploading an image")
        print("3. Enjoy automatic background removal!")
        
        return True
        
    finally:
        # Clean up
        if server_process:
            print("\n🧹 Cleaning up...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except:
                server_process.kill()
        
        # Clean up test files
        if os.path.exists('test_result.png'):
            os.remove('test_result.png')

def main():
    """Main test function"""
    try:
        success = run_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error during testing: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()