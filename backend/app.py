import os
import io
import uuid
import time
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image, ImageFilter, ImageEnhance
import rembg
import cv2
import numpy as np
from werkzeug.utils import secure_filename
import logging
from concurrent.futures import ThreadPoolExecutor
import redis
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
UPLOAD_FOLDER = 'uploads'
RESULT_FOLDER = 'results'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Create directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

# Initialize Redis for caching (optional)
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    redis_client.ping()
    REDIS_AVAILABLE = True
    logger.info("Redis connected successfully")
except:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, caching disabled")

# Initialize REMBG models
AVAILABLE_MODELS = {
    'general': 'u2net',
    'human': 'u2net_human_seg',
    'object': 'silueta',
    'advanced': 'isnet-general-use'
}

# Thread pool for async processing
executor = ThreadPoolExecutor(max_workers=4)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def optimize_image_for_processing(image, max_size=1024):
    """Optimize image size for faster processing while maintaining quality"""
    width, height = image.size
    if max(width, height) > max_size:
        ratio = max_size / max(width, height)
        new_width = int(width * ratio)
        new_height = int(height * ratio)
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    return image

def enhance_edges(image, mask):
    """Apply edge enhancement for better hair and soft edge handling"""
    # Convert to numpy arrays
    img_array = np.array(image)
    mask_array = np.array(mask.convert('L'))
    
    # Apply Gaussian blur to soften edges
    blurred_mask = cv2.GaussianBlur(mask_array, (3, 3), 0)
    
    # Create feathered mask
    feathered_mask = cv2.GaussianBlur(blurred_mask, (5, 5), 2)
    
    # Combine original and feathered mask for better edges
    final_mask = cv2.addWeighted(mask_array, 0.7, feathered_mask, 0.3, 0)
    
    return Image.fromarray(final_mask).convert('L')

def remove_color_spill(image, mask, spill_range=10):
    """Remove color spill from background"""
    img_array = np.array(image.convert('RGBA'))
    mask_array = np.array(mask.convert('L'))
    
    # Create inverted mask to identify background bleeding areas
    inverted_mask = 255 - mask_array
    
    # Apply median filter to reduce noise
    filtered_mask = cv2.medianBlur(inverted_mask, 5)
    
    # Create final result
    img_array[:, :, 3] = mask_array
    
    return Image.fromarray(img_array, 'RGBA')

def process_background_removal(image_path, model_name='general', enhance_edges_flag=True):
    """Main background removal processing function"""
    try:
        # Load image
        original_image = Image.open(image_path).convert('RGB')
        
        # Store original dimensions
        original_size = original_image.size
        
        # Optimize for processing
        processing_image = optimize_image_for_processing(original_image)
        
        # Select model
        model_key = AVAILABLE_MODELS.get(model_name, 'u2net')
        logger.info(f"Using model: {model_key}")
        
        # Remove background
        result = rembg.remove(processing_image, model_name=model_key)
        
        # Resize back to original dimensions if different
        if processing_image.size != original_size:
            result = result.resize(original_size, Image.Resampling.LANCZOS)
        
        # Extract mask for further processing
        mask = result.split()[-1]  # Alpha channel
        
        # Enhance edges if requested
        if enhance_edges_flag:
            enhanced_mask = enhance_edges(original_image, mask)
            
            # Apply enhanced mask
            result_array = np.array(original_image.convert('RGBA'))
            result_array[:, :, 3] = np.array(enhanced_mask)
            result = Image.fromarray(result_array, 'RGBA')
        
        # Remove color spill
        result = remove_color_spill(original_image, mask)
        
        return result, mask
        
    except Exception as e:
        logger.error(f"Error in background removal: {str(e)}")
        raise

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'available_models': list(AVAILABLE_MODELS.keys()),
        'redis_available': REDIS_AVAILABLE
    })

@app.route('/api/upload', methods=['POST'])
def upload_image():
    """Upload and process image for background removal"""
    try:
        # Check if file is present
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Only PNG, JPG, and JPEG are allowed'}), 400
        
        # Get processing parameters
        model_name = request.form.get('model', 'general')
        enhance_edges_flag = request.form.get('enhance_edges', 'true').lower() == 'true'
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        filename = secure_filename(f"{file_id}.{file.filename.rsplit('.', 1)[1].lower()}")
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        # Save uploaded file
        file.save(file_path)
        
        # Check Redis cache
        cache_key = f"bg_removal:{file_id}:{model_name}:{enhance_edges_flag}"
        if REDIS_AVAILABLE:
            cached_result = redis_client.get(cache_key)
            if cached_result:
                logger.info("Returning cached result")
                return jsonify({
                    'success': True,
                    'file_id': file_id,
                    'cached': True
                })
        
        # Process image
        start_time = time.time()
        result_image, mask = process_background_removal(file_path, model_name, enhance_edges_flag)
        processing_time = time.time() - start_time
        
        # Save result
        result_filename = f"{file_id}_result.png"
        result_path = os.path.join(RESULT_FOLDER, result_filename)
        result_image.save(result_path, 'PNG', optimize=True)
        
        # Save mask separately for editing
        mask_filename = f"{file_id}_mask.png"
        mask_path = os.path.join(RESULT_FOLDER, mask_filename)
        mask.save(mask_path, 'PNG')
        
        # Cache result in Redis
        if REDIS_AVAILABLE:
            redis_client.setex(cache_key, 3600, result_filename)  # Cache for 1 hour
        
        # Clean up uploaded file
        os.remove(file_path)
        
        logger.info(f"Background removal completed in {processing_time:.2f} seconds")
        
        return jsonify({
            'success': True,
            'file_id': file_id,
            'processing_time': round(processing_time, 2),
            'model_used': model_name,
            'cached': False
        })
        
    except Exception as e:
        logger.error(f"Error in upload_image: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/download/<file_id>', methods=['GET'])
def download_result(file_id):
    """Download processed image"""
    try:
        result_filename = f"{file_id}_result.png"
        result_path = os.path.join(RESULT_FOLDER, result_filename)
        
        if not os.path.exists(result_path):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(
            result_path,
            as_attachment=True,
            download_name=f"background_removed_{file_id}.png",
            mimetype='image/png'
        )
        
    except Exception as e:
        logger.error(f"Error in download_result: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/preview/<file_id>', methods=['GET'])
def preview_result(file_id):
    """Get base64 encoded preview of the result"""
    try:
        result_filename = f"{file_id}_result.png"
        result_path = os.path.join(RESULT_FOLDER, result_filename)
        
        if not os.path.exists(result_path):
            return jsonify({'error': 'File not found'}), 404
        
        # Create thumbnail for preview
        with Image.open(result_path) as img:
            img.thumbnail((400, 400), Image.Resampling.LANCZOS)
            
            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            
        return jsonify({
            'success': True,
            'preview': f"data:image/png;base64,{img_base64}"
        })
        
    except Exception as e:
        logger.error(f"Error in preview_result: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/edit-mask', methods=['POST'])
def edit_mask():
    """Apply manual edits to the mask"""
    try:
        data = request.get_json()
        file_id = data.get('file_id')
        edits = data.get('edits', [])  # Array of edit operations
        
        mask_filename = f"{file_id}_mask.png"
        mask_path = os.path.join(RESULT_FOLDER, mask_filename)
        
        if not os.path.exists(mask_path):
            return jsonify({'error': 'Mask file not found'}), 404
        
        # Load mask
        mask = Image.open(mask_path).convert('L')
        mask_array = np.array(mask)
        
        # Apply edits
        for edit in edits:
            edit_type = edit.get('type')
            coordinates = edit.get('coordinates', [])
            
            if edit_type == 'add' and coordinates:
                # Add to mask (restore area)
                for coord in coordinates:
                    x, y, radius = coord['x'], coord['y'], coord.get('radius', 10)
                    cv2.circle(mask_array, (x, y), radius, 255, -1)
            
            elif edit_type == 'remove' and coordinates:
                # Remove from mask
                for coord in coordinates:
                    x, y, radius = coord['x'], coord['y'], coord.get('radius', 10)
                    cv2.circle(mask_array, (x, y), radius, 0, -1)
        
        # Save updated mask
        updated_mask = Image.fromarray(mask_array, 'L')
        updated_mask.save(mask_path, 'PNG')
        
        # Regenerate result with updated mask
        result_filename = f"{file_id}_result.png"
        result_path = os.path.join(RESULT_FOLDER, result_filename)
        
        # Apply new mask to original result
        result = Image.open(result_path).convert('RGBA')
        result_array = np.array(result)
        result_array[:, :, 3] = mask_array
        
        updated_result = Image.fromarray(result_array, 'RGBA')
        updated_result.save(result_path, 'PNG', optimize=True)
        
        return jsonify({'success': True, 'message': 'Mask updated successfully'})
        
    except Exception as e:
        logger.error(f"Error in edit_mask: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)