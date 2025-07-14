import os
import io
import uuid
import redis
import numpy as np
from PIL import Image, ImageFilter
import cv2
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import rembg
from rembg import remove, new_session
import torch
from celery import Celery
import base64
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESULT_FOLDER'] = 'results'
app.config['REDIS_URL'] = os.getenv('REDIS_URL', 'redis://localhost:6379')
app.config['CELERY_BROKER_URL'] = app.config['REDIS_URL']

# Initialize Redis for caching
try:
    redis_client = redis.from_url(app.config['REDIS_URL'])
    redis_client.ping()
    logger.info("Redis connected successfully")
except:
    redis_client = None
    logger.warning("Redis not available, caching disabled")

# Initialize Celery for background processing
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

# Create directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULT_FOLDER'], exist_ok=True)

class BackgroundRemovalService:
    def __init__(self):
        """Initialize the background removal service with multiple model options"""
        self.models = {}
        self.load_models()
        
    def load_models(self):
        """Load different models for various use cases"""
        try:
            # U²-Net - Best general purpose model
            self.models['u2net'] = new_session('u2net')
            logger.info("U²-Net model loaded successfully")
            
            # U²-Net Human Segmentation - Optimized for people
            self.models['u2net_human_seg'] = new_session('u2net_human_seg')
            logger.info("U²-Net Human Segmentation model loaded")
            
            # SILUETA - Good for products
            self.models['silueta'] = new_session('silueta')
            logger.info("SILUETA model loaded")
            
        except Exception as e:
            logger.error(f"Error loading models: {e}")
    
    def detect_subject_type(self, image):
        """Detect if the image contains people, products, or other subjects"""
        # Simple heuristic based on image characteristics
        # In production, you might use a separate classification model
        gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
        
        # Detect faces using OpenCV
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        if len(faces) > 0:
            return 'person'
        
        # Additional heuristics could be added here
        # For now, default to general purpose
        return 'general'
    
    def preprocess_image(self, image, max_size=1024):
        """Preprocess image for optimal processing"""
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize if too large, maintaining aspect ratio
        width, height = image.size
        if max(width, height) > max_size:
            ratio = max_size / max(width, height)
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return image
    
    def enhance_edges(self, mask, feather_radius=2):
        """Enhance mask edges with feathering"""
        # Convert PIL to numpy
        mask_array = np.array(mask)
        
        # Apply Gaussian blur for feathering
        if feather_radius > 0:
            mask_array = cv2.GaussianBlur(mask_array, (feather_radius*2+1, feather_radius*2+1), 0)
        
        # Enhance edge contrast
        mask_array = cv2.convertScaleAbs(mask_array, alpha=1.2, beta=10)
        
        return Image.fromarray(mask_array)
    
    def refine_hair_details(self, image, mask):
        """Special processing for hair and fine details"""
        # Convert to numpy arrays
        img_array = np.array(image)
        mask_array = np.array(mask)
        
        # Apply bilateral filter to preserve edges while smoothing
        refined_mask = cv2.bilateralFilter(mask_array, 9, 75, 75)
        
        # Use morphological operations to clean up the mask
        kernel = np.ones((3,3), np.uint8)
        refined_mask = cv2.morphologyEx(refined_mask, cv2.MORPH_CLOSE, kernel)
        refined_mask = cv2.morphologyEx(refined_mask, cv2.MORPH_OPEN, kernel)
        
        return Image.fromarray(refined_mask)
    
    def process_image(self, image, model_type='auto', quality='high', feather_radius=2):
        """Main processing function with advanced options"""
        try:
            # Determine best model if auto
            if model_type == 'auto':
                subject_type = self.detect_subject_type(image)
                if subject_type == 'person':
                    model_type = 'u2net_human_seg'
                else:
                    model_type = 'u2net'
            
            # Preprocess image
            processed_image = self.preprocess_image(image)
            
            # Get the selected model
            model_session = self.models.get(model_type, self.models['u2net'])
            
            # Remove background
            result = remove(processed_image, session=model_session)
            
            # Extract alpha channel as mask for further processing
            if result.mode == 'RGBA':
                mask = result.split()[-1]  # Get alpha channel
                
                # Apply enhancements based on quality setting
                if quality == 'high':
                    mask = self.refine_hair_details(processed_image, mask)
                    mask = self.enhance_edges(mask, feather_radius)
                
                # Reconstruct the final image with enhanced mask
                final_result = Image.new('RGBA', processed_image.size, (0, 0, 0, 0))
                final_result.paste(processed_image, (0, 0))
                final_result.putalpha(mask)
                
                return final_result
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            raise

# Initialize the service
bg_removal_service = BackgroundRemovalService()

def allowed_file(filename):
    """Check if uploaded file is allowed"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_cache_key(image_hash, model_type, quality, feather_radius):
    """Generate cache key for processed images"""
    return f"bg_removal:{image_hash}:{model_type}:{quality}:{feather_radius}"

def get_image_hash(image_data):
    """Generate hash for image data for caching"""
    import hashlib
    return hashlib.md5(image_data).hexdigest()

@celery.task
def process_image_async(image_data, model_type, quality, feather_radius, task_id):
    """Async background processing task"""
    try:
        # Convert base64 back to image
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        
        # Process the image
        result = bg_removal_service.process_image(image, model_type, quality, feather_radius)
        
        # Save result
        result_path = os.path.join(app.config['RESULT_FOLDER'], f"{task_id}.png")
        result.save(result_path, 'PNG')
        
        # Cache the result if Redis is available
        if redis_client:
            try:
                # Store result path in cache
                cache_key = f"task_result:{task_id}"
                redis_client.setex(cache_key, 3600, result_path)  # 1 hour expiry
            except:
                pass
        
        return {"status": "completed", "result_path": result_path}
        
    except Exception as e:
        logger.error(f"Async processing error: {e}")
        return {"status": "error", "error": str(e)}

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "models_loaded": len(bg_removal_service.models),
        "redis_available": redis_client is not None
    })

@app.route('/api/remove-background', methods=['POST'])
def remove_background():
    """Main endpoint for background removal"""
    try:
        # Check if file was uploaded
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"error": "File type not allowed"}), 400
        
        # Get processing options
        model_type = request.form.get('model', 'auto')
        quality = request.form.get('quality', 'high')
        feather_radius = int(request.form.get('feather_radius', 2))
        async_processing = request.form.get('async', 'false').lower() == 'true'
        
        # Read and validate image
        image_data = file.read()
        if len(image_data) > app.config['MAX_CONTENT_LENGTH']:
            return jsonify({"error": "File too large"}), 400
        
        # Check cache first
        image_hash = get_image_hash(image_data)
        cache_key = generate_cache_key(image_hash, model_type, quality, feather_radius)
        
        if redis_client:
            try:
                cached_result = redis_client.get(cache_key)
                if cached_result:
                    logger.info("Returning cached result")
                    return jsonify({
                        "status": "completed",
                        "cached": True,
                        "download_url": f"/api/download/{cached_result.decode()}"
                    })
            except:
                pass
        
        image = Image.open(io.BytesIO(image_data))
        
        # Handle async processing
        if async_processing:
            task_id = str(uuid.uuid4())
            image_b64 = base64.b64encode(image_data).decode()
            task = process_image_async.delay(image_b64, model_type, quality, feather_radius, task_id)
            
            return jsonify({
                "status": "processing",
                "task_id": task_id,
                "check_url": f"/api/status/{task_id}"
            })
        
        # Synchronous processing
        result = bg_removal_service.process_image(image, model_type, quality, feather_radius)
        
        # Save result
        result_id = str(uuid.uuid4())
        result_path = os.path.join(app.config['RESULT_FOLDER'], f"{result_id}.png")
        result.save(result_path, 'PNG')
        
        # Cache the result
        if redis_client:
            try:
                redis_client.setex(cache_key, 3600, result_id)  # 1 hour expiry
            except:
                pass
        
        return jsonify({
            "status": "completed",
            "result_id": result_id,
            "download_url": f"/api/download/{result_id}",
            "processing_time": "sync"
        })
        
    except Exception as e:
        logger.error(f"Error in remove_background: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/status/<task_id>', methods=['GET'])
def check_status(task_id):
    """Check status of async processing task"""
    try:
        if redis_client:
            cache_key = f"task_result:{task_id}"
            result = redis_client.get(cache_key)
            if result:
                result_path = result.decode()
                result_id = os.path.basename(result_path).replace('.png', '')
                return jsonify({
                    "status": "completed",
                    "result_id": result_id,
                    "download_url": f"/api/download/{result_id}"
                })
        
        # Check Celery task status
        task = process_image_async.AsyncResult(task_id)
        if task.state == 'PENDING':
            return jsonify({"status": "processing"})
        elif task.state == 'SUCCESS':
            result = task.result
            if result.get("status") == "completed":
                result_id = os.path.basename(result["result_path"]).replace('.png', '')
                return jsonify({
                    "status": "completed",
                    "result_id": result_id,
                    "download_url": f"/api/download/{result_id}"
                })
        else:
            return jsonify({"status": "error", "error": str(task.info)})
            
        return jsonify({"status": "processing"})
        
    except Exception as e:
        logger.error(f"Error checking status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/download/<result_id>', methods=['GET'])
def download_result(result_id):
    """Download processed image"""
    try:
        result_path = os.path.join(app.config['RESULT_FOLDER'], f"{result_id}.png")
        if not os.path.exists(result_path):
            return jsonify({"error": "Result not found"}), 404
        
        return send_file(
            result_path,
            as_attachment=True,
            download_name=f"background_removed_{result_id}.png",
            mimetype='image/png'
        )
        
    except Exception as e:
        logger.error(f"Error downloading result: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/preview/<result_id>', methods=['GET'])
def preview_result(result_id):
    """Preview processed image without download"""
    try:
        result_path = os.path.join(app.config['RESULT_FOLDER'], f"{result_id}.png")
        if not os.path.exists(result_path):
            return jsonify({"error": "Result not found"}), 404
        
        return send_file(result_path, mimetype='image/png')
        
    except Exception as e:
        logger.error(f"Error previewing result: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/models', methods=['GET'])
def get_available_models():
    """Get list of available models"""
    return jsonify({
        "models": list(bg_removal_service.models.keys()),
        "default": "u2net",
        "descriptions": {
            "u2net": "General purpose, excellent for most subjects",
            "u2net_human_seg": "Optimized for people and portraits",
            "silueta": "Good for products and objects"
        }
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)