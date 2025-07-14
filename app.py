import os
import io
import json
import hashlib
from typing import Optional, Tuple, Dict, Any
import logging
from datetime import datetime, timedelta

import torch
import torch.nn.functional as F
from torchvision import transforms
from PIL import Image, ImageFilter
import numpy as np
import cv2
from transformers import AutoModelForImageSegmentation
import requests

from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
app.config.update({
    'MAX_CONTENT_LENGTH': 50 * 1024 * 1024,  # 50MB max file size
    'UPLOAD_FOLDER': 'uploads',
    'OUTPUT_FOLDER': 'outputs',
    'SECRET_KEY': os.environ.get('SECRET_KEY', 'dev-secret-key'),
    'REMOVE_BG_API_KEY': os.environ.get('REMOVE_BG_API_KEY'),
    'ENABLE_REMOVE_BG_FALLBACK': os.environ.get('ENABLE_REMOVE_BG_FALLBACK', 'false').lower() == 'true',
    'MODEL_CACHE_DIR': 'models',
    'REDIS_URL': os.environ.get('REDIS_URL', 'redis://localhost:6379'),
})

# Rate limiting
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["1000 per hour", "100 per minute"]
)

# Ensure directories exist
for folder in [app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER'], app.config['MODEL_CACHE_DIR']]:
    os.makedirs(folder, exist_ok=True)

# Global model variable
background_removal_model = None
device = "cuda" if torch.cuda.is_available() else "cpu"

class BackgroundRemovalService:
    """Handles background removal using multiple models and APIs"""
    
    def __init__(self):
        self.model = None
        self.device = device
        self.load_model()
        
    def load_model(self):
        """Load the Bria RMBG 2.0 model"""
        try:
            logger.info(f"Loading RMBG 2.0 model on {self.device}")
            self.model = AutoModelForImageSegmentation.from_pretrained(
                'briaai/RMBG-2.0',
                trust_remote_code=True,
                cache_dir=app.config['MODEL_CACHE_DIR']
            )
            if torch.cuda.is_available():
                torch.set_float32_matmul_precision(['high', 'highest'][0])
            self.model.to(self.device)
            self.model.eval()
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self.model = None
    
    def preprocess_image(self, image: Image.Image, target_size: tuple = (1024, 1024)) -> torch.Tensor:
        """Preprocess image for model inference"""
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize while maintaining aspect ratio
        image = self._resize_with_aspect_ratio(image, target_size)
        
        # Transform for model
        transform = transforms.Compose([
            transforms.Resize(target_size),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])
        
        return transform(image).unsqueeze(0).to(self.device)
    
    def _resize_with_aspect_ratio(self, image: Image.Image, target_size: tuple) -> Image.Image:
        """Resize image maintaining aspect ratio"""
        width, height = image.size
        target_width, target_height = target_size
        
        # Calculate aspect ratios
        image_aspect = width / height
        target_aspect = target_width / target_height
        
        if image_aspect > target_aspect:
            # Image is wider - fit to width
            new_width = target_width
            new_height = int(target_width / image_aspect)
        else:
            # Image is taller - fit to height
            new_height = target_height
            new_width = int(target_height * image_aspect)
        
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    def remove_background_local(self, image: Image.Image) -> Tuple[Image.Image, float]:
        """Remove background using local RMBG 2.0 model"""
        if self.model is None:
            raise RuntimeError("Model not loaded")
        
        original_size = image.size
        
        # Preprocess
        input_tensor = self.preprocess_image(image)
        
        # Inference
        with torch.no_grad():
            predictions = self.model(input_tensor)[-1].sigmoid().cpu()
        
        # Post-process
        mask = predictions[0].squeeze()
        mask_pil = transforms.ToPILImage()(mask)
        mask_resized = mask_pil.resize(original_size, Image.Resampling.LANCZOS)
        
        # Apply mask to original image
        result = image.copy()
        result.putalpha(mask_resized)
        
        # Calculate confidence score (average mask confidence)
        confidence = float(torch.mean(predictions).item())
        
        return result, confidence
    
    def remove_background_api(self, image: Image.Image, api_key: str) -> Tuple[Image.Image, float]:
        """Remove background using Remove.bg API as fallback"""
        # Convert image to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        response = requests.post(
            'https://api.remove.bg/v1.0/removebg',
            files={'image_file': img_byte_arr},
            data={'size': 'auto'},
            headers={'X-Api-Key': api_key},
            timeout=30
        )
        
        if response.status_code == requests.codes.ok:
            result_image = Image.open(io.BytesIO(response.content))
            return result_image, 0.95  # Assume high confidence for Remove.bg
        else:
            raise RuntimeError(f"Remove.bg API error: {response.status_code} - {response.text}")
    
    def enhance_edges(self, image: Image.Image, feather_radius: float = 1.0) -> Image.Image:
        """Enhance edges of the cutout image"""
        if image.mode != 'RGBA':
            return image
        
        # Extract alpha channel
        alpha = image.split()[-1]
        
        # Apply slight blur to soften edges
        if feather_radius > 0:
            alpha = alpha.filter(ImageFilter.GaussianBlur(radius=feather_radius))
        
        # Reconstruct image
        result = Image.merge('RGBA', (*image.split()[:-1], alpha))
        return result
    
    def remove_background(self, image: Image.Image, use_api_fallback: bool = False, 
                         enhance_edges: bool = True, feather_radius: float = 1.0) -> Dict[str, Any]:
        """Main background removal function with fallback options"""
        try:
            # Try local model first
            if not use_api_fallback and self.model is not None:
                result, confidence = self.remove_background_local(image)
                method = "RMBG-2.0 (Local)"
            elif app.config['ENABLE_REMOVE_BG_FALLBACK'] and app.config['REMOVE_BG_API_KEY']:
                result, confidence = self.remove_background_api(image, app.config['REMOVE_BG_API_KEY'])
                method = "Remove.bg API"
            else:
                raise RuntimeError("No background removal method available")
            
            # Enhance edges if requested
            if enhance_edges:
                result = self.enhance_edges(result, feather_radius)
            
            return {
                'image': result,
                'confidence': confidence,
                'method': method,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Background removal failed: {e}")
            return {
                'error': str(e),
                'success': False
            }

# Initialize service
bg_service = BackgroundRemovalService()

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    allowed_extensions = {'png', 'jpg', 'jpeg', 'webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def get_file_hash(file_content: bytes) -> str:
    """Generate hash for file caching"""
    return hashlib.md5(file_content).hexdigest()

@app.route('/')
def index():
    """Serve the main application page"""
    return render_template('index.html')

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'model_loaded': bg_service.model is not None,
        'device': device,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/remove-background', methods=['POST'])
@limiter.limit("30 per minute")
def remove_background_endpoint():
    """Main background removal endpoint"""
    try:
        # Check if file is present
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed. Use PNG, JPG, JPEG, or WebP'}), 400
        
        # Read file content
        file_content = file.read()
        if len(file_content) == 0:
            return jsonify({'error': 'Empty file'}), 400
        
        # Get processing options
        enhance_edges = request.form.get('enhance_edges', 'true').lower() == 'true'
        feather_radius = float(request.form.get('feather_radius', '1.0'))
        use_api_fallback = request.form.get('use_api_fallback', 'false').lower() == 'true'
        
        # Load image
        try:
            image = Image.open(io.BytesIO(file_content))
        except Exception as e:
            return jsonify({'error': f'Invalid image file: {str(e)}'}), 400
        
        # Check image size
        if image.size[0] * image.size[1] > 4000 * 4000:
            return jsonify({'error': 'Image too large. Maximum 4000x4000 pixels'}), 400
        
        # Process image
        result = bg_service.remove_background(
            image, 
            use_api_fallback=use_api_fallback,
            enhance_edges=enhance_edges,
            feather_radius=feather_radius
        )
        
        if not result['success']:
            return jsonify({'error': result['error']}), 500
        
        # Save result
        filename = secure_filename(file.filename or 'image.png')
        name_part = filename.rsplit('.', 1)[0]
        output_filename = f"{name_part}_no_bg_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        
        result['image'].save(output_path, 'PNG', optimize=True)
        
        return jsonify({
            'success': True,
            'confidence': result['confidence'],
            'method': result['method'],
            'filename': output_filename,
            'download_url': f'/api/download/{output_filename}',
            'processing_time': 'calculated on frontend'
        })
        
    except RequestEntityTooLarge:
        return jsonify({'error': 'File too large. Maximum 50MB allowed'}), 413
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/download/<filename>')
def download_file(filename):
    """Download processed image"""
    try:
        file_path = os.path.join(app.config['OUTPUT_FOLDER'], secure_filename(filename))
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(
            file_path,
            mimetype='image/png',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({'error': 'Download failed'}), 500

@app.route('/api/batch-remove', methods=['POST'])
@limiter.limit("5 per minute")
def batch_remove_background():
    """Batch background removal endpoint"""
    try:
        files = request.files.getlist('images')
        
        if not files or len(files) == 0:
            return jsonify({'error': 'No images provided'}), 400
        
        if len(files) > 10:
            return jsonify({'error': 'Maximum 10 images per batch'}), 400
        
        results = []
        
        for i, file in enumerate(files):
            if not allowed_file(file.filename):
                results.append({
                    'index': i,
                    'filename': file.filename,
                    'success': False,
                    'error': 'Invalid file type'
                })
                continue
            
            try:
                file_content = file.read()
                image = Image.open(io.BytesIO(file_content))
                
                # Process image
                result = bg_service.remove_background(image)
                
                if result['success']:
                    # Save result
                    filename = secure_filename(file.filename or f'image_{i}.png')
                    name_part = filename.rsplit('.', 1)[0]
                    output_filename = f"{name_part}_no_bg_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
                    
                    result['image'].save(output_path, 'PNG', optimize=True)
                    
                    results.append({
                        'index': i,
                        'filename': file.filename,
                        'success': True,
                        'confidence': result['confidence'],
                        'method': result['method'],
                        'output_filename': output_filename,
                        'download_url': f'/api/download/{output_filename}'
                    })
                else:
                    results.append({
                        'index': i,
                        'filename': file.filename,
                        'success': False,
                        'error': result['error']
                    })
                    
            except Exception as e:
                results.append({
                    'index': i,
                    'filename': file.filename,
                    'success': False,
                    'error': str(e)
                })
        
        return jsonify({
            'success': True,
            'results': results,
            'total_processed': len([r for r in results if r['success']]),
            'total_failed': len([r for r in results if not r['success']])
        })
        
    except Exception as e:
        logger.error(f"Batch processing error: {e}")
        return jsonify({'error': 'Batch processing failed'}), 500

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum 50MB allowed'}), 413

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)