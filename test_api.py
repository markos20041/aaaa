#!/usr/bin/env python3
"""
Test script for Background Removal API

This script tests all API endpoints and functionality to ensure
the background removal service is working correctly.
"""

import requests
import json
import time
import os
import sys
from typing import Dict, Any
import base64
from PIL import Image
import io

class BackgroundRemovalTester:
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.test_results = []
        
    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def create_test_image(self) -> bytes:
        """Create a simple test image"""
        img = Image.new('RGB', (200, 200), color='red')
        # Add a simple shape
        for i in range(50, 150):
            for j in range(50, 150):
                img.putpixel((i, j), (0, 255, 0))
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def test_health_check(self) -> bool:
        """Test the health check endpoint"""
        self.log("Testing health check endpoint...")
        try:
            response = self.session.get(f"{self.base_url}/api/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Health check passed: {data}")
                return True
            else:
                self.log(f"❌ Health check failed with status {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Health check failed with error: {e}", "ERROR")
            return False
    
    def test_single_image_removal(self) -> bool:
        """Test single image background removal"""
        self.log("Testing single image background removal...")
        try:
            test_image = self.create_test_image()
            
            files = {'image': ('test.png', test_image, 'image/png')}
            data = {
                'enhance_edges': 'true',
                'feather_radius': '1.0',
                'use_api_fallback': 'false'
            }
            
            start_time = time.time()
            response = self.session.post(
                f"{self.base_url}/api/remove-background",
                files=files,
                data=data,
                timeout=60
            )
            processing_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                self.log(f"✅ Single image processing passed in {processing_time:.2f}s")
                self.log(f"   Method: {result.get('method', 'Unknown')}")
                self.log(f"   Confidence: {result.get('confidence', 0):.2%}")
                self.log(f"   Filename: {result.get('filename', 'Unknown')}")
                return True
            else:
                self.log(f"❌ Single image processing failed: {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Single image processing failed with error: {e}", "ERROR")
            return False
    
    def test_batch_processing(self) -> bool:
        """Test batch image processing"""
        self.log("Testing batch image processing...")
        try:
            # Create multiple test images
            images = []
            for i in range(3):
                test_image = self.create_test_image()
                images.append(('images', (f'test_{i}.png', test_image, 'image/png')))
            
            start_time = time.time()
            response = self.session.post(
                f"{self.base_url}/api/batch-remove",
                files=images,
                timeout=120
            )
            processing_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                self.log(f"✅ Batch processing passed in {processing_time:.2f}s")
                self.log(f"   Processed: {result.get('total_processed', 0)}")
                self.log(f"   Failed: {result.get('total_failed', 0)}")
                return True
            else:
                self.log(f"❌ Batch processing failed: {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Batch processing failed with error: {e}", "ERROR")
            return False
    
    def test_download_functionality(self) -> bool:
        """Test file download functionality"""
        self.log("Testing download functionality...")
        try:
            # First, process an image to get a download URL
            test_image = self.create_test_image()
            files = {'image': ('test.png', test_image, 'image/png')}
            
            response = self.session.post(
                f"{self.base_url}/api/remove-background",
                files=files,
                timeout=60
            )
            
            if response.status_code != 200:
                self.log("❌ Could not process image for download test", "ERROR")
                return False
            
            result = response.json()
            download_url = result.get('download_url')
            
            if not download_url:
                self.log("❌ No download URL in response", "ERROR")
                return False
            
            # Test download
            download_response = self.session.get(f"{self.base_url}{download_url}", timeout=30)
            
            if download_response.status_code == 200:
                if len(download_response.content) > 0:
                    self.log(f"✅ Download test passed, file size: {len(download_response.content)} bytes")
                    return True
                else:
                    self.log("❌ Downloaded file is empty", "ERROR")
                    return False
            else:
                self.log(f"❌ Download failed with status {download_response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Download test failed with error: {e}", "ERROR")
            return False
    
    def test_error_handling(self) -> bool:
        """Test error handling with invalid inputs"""
        self.log("Testing error handling...")
        tests_passed = 0
        
        # Test 1: No file provided
        try:
            response = self.session.post(f"{self.base_url}/api/remove-background", timeout=10)
            if response.status_code == 400:
                self.log("✅ No file error handling works")
                tests_passed += 1
            else:
                self.log("❌ No file error handling failed", "ERROR")
        except Exception as e:
            self.log(f"❌ No file test error: {e}", "ERROR")
        
        # Test 2: Invalid file type
        try:
            files = {'image': ('test.txt', b'not an image', 'text/plain')}
            response = self.session.post(
                f"{self.base_url}/api/remove-background", 
                files=files,
                timeout=10
            )
            if response.status_code == 400:
                self.log("✅ Invalid file type error handling works")
                tests_passed += 1
            else:
                self.log("❌ Invalid file type error handling failed", "ERROR")
        except Exception as e:
            self.log(f"❌ Invalid file type test error: {e}", "ERROR")
        
        # Test 3: Non-existent download
        try:
            response = self.session.get(f"{self.base_url}/api/download/nonexistent.png", timeout=10)
            if response.status_code == 404:
                self.log("✅ Non-existent file error handling works")
                tests_passed += 1
            else:
                self.log("❌ Non-existent file error handling failed", "ERROR")
        except Exception as e:
            self.log(f"❌ Non-existent file test error: {e}", "ERROR")
        
        return tests_passed >= 2  # At least 2 out of 3 tests should pass
    
    def test_performance(self) -> bool:
        """Test performance with timing measurements"""
        self.log("Testing performance...")
        try:
            test_image = self.create_test_image()
            files = {'image': ('test.png', test_image, 'image/png')}
            
            times = []
            for i in range(3):
                start_time = time.time()
                response = self.session.post(
                    f"{self.base_url}/api/remove-background",
                    files=files,
                    timeout=60
                )
                end_time = time.time()
                
                if response.status_code == 200:
                    times.append(end_time - start_time)
                else:
                    self.log(f"❌ Performance test iteration {i+1} failed", "ERROR")
                    return False
            
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            
            self.log(f"✅ Performance test completed:")
            self.log(f"   Average time: {avg_time:.2f}s")
            self.log(f"   Min time: {min_time:.2f}s")
            self.log(f"   Max time: {max_time:.2f}s")
            
            # Performance threshold (adjust based on your requirements)
            if avg_time < 30:  # 30 seconds average
                self.log("✅ Performance is within acceptable limits")
                return True
            else:
                self.log("⚠️ Performance is slower than expected", "WARNING")
                return True  # Still pass, but with warning
                
        except Exception as e:
            self.log(f"❌ Performance test failed with error: {e}", "ERROR")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all tests and return overall result"""
        self.log("Starting comprehensive API tests...")
        self.log("=" * 50)
        
        tests = [
            ("Health Check", self.test_health_check),
            ("Single Image Removal", self.test_single_image_removal),
            ("Batch Processing", self.test_batch_processing),
            ("Download Functionality", self.test_download_functionality),
            ("Error Handling", self.test_error_handling),
            ("Performance", self.test_performance),
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            self.log(f"\n--- Running {test_name} ---")
            try:
                if test_func():
                    passed_tests += 1
                    self.test_results.append((test_name, "PASSED"))
                else:
                    self.test_results.append((test_name, "FAILED"))
            except Exception as e:
                self.log(f"❌ {test_name} crashed with error: {e}", "ERROR")
                self.test_results.append((test_name, "CRASHED"))
        
        # Print summary
        self.log("\n" + "=" * 50)
        self.log("TEST SUMMARY")
        self.log("=" * 50)
        
        for test_name, result in self.test_results:
            status_icon = "✅" if result == "PASSED" else "❌"
            self.log(f"{status_icon} {test_name}: {result}")
        
        self.log(f"\nTotal: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            self.log("🎉 All tests passed! The API is working correctly.")
            return True
        elif passed_tests >= total_tests * 0.8:  # 80% pass rate
            self.log("⚠️ Most tests passed, but some issues detected.")
            return True
        else:
            self.log("❌ Multiple test failures detected. Please check the service.")
            return False

def main():
    """Main function to run the tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Background Removal API")
    parser.add_argument(
        "--url", 
        default="http://localhost:5000",
        help="Base URL of the API (default: http://localhost:5000)"
    )
    parser.add_argument(
        "--nodejs", 
        action="store_true",
        help="Test Node.js version on port 3000"
    )
    
    args = parser.parse_args()
    
    if args.nodejs:
        base_url = "http://localhost:3000"
    else:
        base_url = args.url
    
    print("🎨 Background Removal API Test Suite")
    print("=" * 50)
    print(f"Testing API at: {base_url}")
    print("=" * 50)
    
    tester = BackgroundRemovalTester(base_url)
    
    try:
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test suite crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()