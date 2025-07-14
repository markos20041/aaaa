#!/usr/bin/env python3
"""
Example usage of the AI Background Removal API

This script demonstrates how to:
1. Process a single image
2. Handle different models and parameters
3. Save results with transparent background
4. Process multiple images in batch
5. Refine masks manually

Run the Flask app first: python app.py
Then run this script: python example_usage.py
"""

import requests
import base64
import json
from pathlib import Path
from PIL import Image
import io

# Configuration
API_BASE_URL = "http://localhost:5000"
SAMPLE_IMAGE_PATH = "sample_image.jpg"  # Place a sample image here

def test_server_health():
    """Test if the server is running and healthy"""
    print("🔍 Testing server health...")
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        data = response.json()
        print(f"✅ Server Status: {data['status']}")
        print(f"📋 Available Models: {data['available_models']}")
        print(f"💻 Device: {data['device']}")
        return True
    except Exception as e:
        print(f"❌ Server not accessible: {e}")
        return False

def remove_background_single_image(image_path, model="rmbg2", enhance_edges=True, feather_amount=0.5):
    """Remove background from a single image"""
    print(f"\n🎨 Processing single image: {image_path}")
    print(f"   Model: {model}")
    print(f"   Edge Enhancement: {enhance_edges}")
    print(f"   Feather Amount: {feather_amount}")
    
    try:
        # Prepare the request
        with open(image_path, 'rb') as f:
            files = {'image': f}
            data = {
                'model': model,
                'enhance_edges': str(enhance_edges).lower(),
                'feather_amount': str(feather_amount)
            }
            
            # Send request
            response = requests.post(
                f"{API_BASE_URL}/remove-background-json",
                files=files,
                data=data
            )
        
        if response.status_code == 200:
            result = response.json()
            if result['success']:
                print(f"✅ Processing successful!")
                print(f"   Processing Time: {result['processing_time']}s")
                print(f"   Model Used: {result['model_used']}")
                print(f"   Original Size: {result['original_size']}")
                
                # Save result image
                result_image_data = base64.b64decode(result['result_image'])
                output_path = f"output_no_bg_{Path(image_path).stem}.png"
                with open(output_path, 'wb') as f:
                    f.write(result_image_data)
                print(f"💾 Result saved to: {output_path}")
                
                # Save mask
                mask_data = base64.b64decode(result['mask'])
                mask_path = f"output_mask_{Path(image_path).stem}.png"
                with open(mask_path, 'wb') as f:
                    f.write(mask_data)
                print(f"💾 Mask saved to: {mask_path}")
                
                return output_path, mask_path
            else:
                print(f"❌ Processing failed: {result.get('error', 'Unknown error')}")
        else:
            print(f"❌ Request failed with status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return None, None

def refine_mask_example(mask_path, dilate=1, erode=1):
    """Example of manual mask refinement"""
    print(f"\n🔧 Refining mask: {mask_path}")
    print(f"   Dilate iterations: {dilate}")
    print(f"   Erode iterations: {erode}")
    
    try:
        with open(mask_path, 'rb') as f:
            files = {'mask': f}
            data = {
                'dilate_iterations': str(dilate),
                'erode_iterations': str(erode)
            }
            
            response = requests.post(
                f"{API_BASE_URL}/refine-mask",
                files=files,
                data=data
            )
        
        if response.status_code == 200:
            refined_mask_path = f"refined_{Path(mask_path).name}"
            with open(refined_mask_path, 'wb') as f:
                f.write(response.content)
            print(f"✅ Refined mask saved to: {refined_mask_path}")
            return refined_mask_path
        else:
            print(f"❌ Mask refinement failed with status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error refining mask: {e}")
    
    return None

def batch_process_example(image_paths, model="rmbg2"):
    """Example of batch processing multiple images"""
    print(f"\n📦 Batch processing {len(image_paths)} images...")
    print(f"   Model: {model}")
    
    try:
        # Prepare files for batch upload
        files = []
        for path in image_paths:
            files.append(('images', open(path, 'rb')))
        
        data = {
            'model': model,
            'enhance_edges': 'true'
        }
        
        response = requests.post(
            f"{API_BASE_URL}/batch-process",
            files=files,
            data=data
        )
        
        # Close file handles
        for _, file_handle in files:
            file_handle.close()
        
        if response.status_code == 200:
            result = response.json()
            if result['success']:
                print(f"✅ Batch processing completed!")
                print(f"   Total processed: {result['total_processed']}")
                
                # Save batch results
                for i, item in enumerate(result['results']):
                    if item['success']:
                        result_data = base64.b64decode(item['result_image'])
                        output_path = f"batch_output_{i}_{item['filename']}.png"
                        with open(output_path, 'wb') as f:
                            f.write(result_data)
                        print(f"💾 Batch result {i+1} saved to: {output_path}")
                    else:
                        print(f"❌ Batch item {i+1} failed: {item['error']}")
            else:
                print(f"❌ Batch processing failed: {result.get('error', 'Unknown error')}")
        else:
            print(f"❌ Batch request failed with status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Batch processing error: {e}")

def compare_models_example(image_path):
    """Compare results from different models"""
    print(f"\n🔬 Comparing models on: {image_path}")
    
    models = ["rmbg2", "birefnet"]
    results = {}
    
    for model in models:
        print(f"\n   Testing {model}...")
        output_path, mask_path = remove_background_single_image(
            image_path, 
            model=model,
            enhance_edges=True,
            feather_amount=1.0
        )
        if output_path:
            results[model] = {
                'output': output_path,
                'mask': mask_path
            }
    
    print(f"\n📊 Model comparison completed!")
    for model, paths in results.items():
        print(f"   {model}: {paths['output']}")

def create_sample_image():
    """Create a simple sample image for testing if none exists"""
    sample_path = "sample_image.jpg"
    if not Path(sample_path).exists():
        print(f"📸 Creating sample image: {sample_path}")
        
        # Create a simple test image with a colored rectangle on white background
        from PIL import Image, ImageDraw
        
        img = Image.new('RGB', (400, 300), 'white')
        draw = ImageDraw.Draw(img)
        
        # Draw a blue rectangle (our "subject")
        draw.rectangle([100, 75, 300, 225], fill='blue', outline='darkblue', width=3)
        
        # Add some text
        try:
            draw.text((150, 140), "TEST", fill='white')
        except:
            pass  # Font might not be available
        
        img.save(sample_path, 'JPEG')
        print(f"✅ Sample image created: {sample_path}")
    
    return sample_path

def main():
    """Main example function"""
    print("🚀 AI Background Removal API Examples")
    print("=" * 50)
    
    # Test server health
    if not test_server_health():
        print("\n❌ Cannot proceed - server is not accessible")
        print("💡 Make sure to run: python app.py")
        return
    
    # Create or use sample image
    sample_image = create_sample_image()
    
    # Example 1: Single image processing with different parameters
    print("\n" + "="*50)
    print("📝 Example 1: Single Image Processing")
    output_path, mask_path = remove_background_single_image(
        sample_image,
        model="rmbg2",
        enhance_edges=True,
        feather_amount=1.0
    )
    
    # Example 2: Manual mask refinement (if mask was generated)
    if mask_path:
        print("\n" + "="*50)
        print("📝 Example 2: Manual Mask Refinement")
        refined_mask = refine_mask_example(mask_path, dilate=2, erode=1)
    
    # Example 3: Compare different models
    print("\n" + "="*50)
    print("📝 Example 3: Model Comparison")
    compare_models_example(sample_image)
    
    # Example 4: Batch processing (if we have multiple images)
    if Path(sample_image).exists():
        print("\n" + "="*50)
        print("📝 Example 4: Batch Processing")
        # For demo, we'll use the same image multiple times
        batch_images = [sample_image] * 2  # Process same image twice
        batch_process_example(batch_images)
    
    print("\n" + "="*50)
    print("✅ All examples completed!")
    print("📁 Check the current directory for output files:")
    print("   - output_no_bg_*.png (background removed images)")
    print("   - output_mask_*.png (alpha masks)")
    print("   - refined_*.png (refined masks)")
    print("   - batch_output_*.png (batch results)")

if __name__ == "__main__":
    main()