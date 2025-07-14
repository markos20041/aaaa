import os
import io
import uuid
import time
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image, ImageFilter, ImageEnhance
import numpy as np
import torch
from transformers import AutoModelForImageSegmentation, AutoProcessor
import cv2
from rembg import remove, new_session
import logging
from werkzeug.utils import secure_filename
import threading
from functools import lru_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'temp_uploads'
app.config['RESULT_FOLDER'] = 'temp_results'

# Create directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULT_FOLDER'], exist_ok=True)

# Global model storage
models = {}
model_lock = threading.Lock()

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'bmp', 'tiff'}

class BackgroundRemover:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {self.device}")
        self.load_models()
    
    def load_models(self):
        """Load background removal models"""
        try:
            # Load RMBG-1.4 model (best accuracy)
            logger.info("Loading RMBG-1.4 model...")
            self.rmbg_model = AutoModelForImageSegmentation.from_pretrained(
                'briaai/RMBG-1.4', 
                trust_remote_code=True
            ).to(self.device)
            self.rmbg_processor = AutoProcessor.from_pretrained(
                'briaai/RMBG-1.4',
                trust_remote_code=True
            )
            
            # Load rembg session for fallback
            logger.info("Loading rembg u2net model...")
            self.rembg_session = new_session('u2net')
            
            logger.info("Models loaded successfully!")
            
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            # Fallback to rembg only
            self.rmbg_model = None
            self.rembg_session = new_session('u2net')
    
    def preprocess_image(self, image):
        """Preprocess image for optimal results"""
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize if too large (for performance)
        max_size = 2048
        if max(image.size) > max_size:
            ratio = max_size / max(image.size)
            new_size = tuple(int(dim * ratio) for dim in image.size)
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        return image
    
    def enhance_edges(self, image, mask, feather_radius=2):
        """Enhance edges and apply feathering"""
        # Convert mask to numpy array
        mask_np = np.array(mask)
        
        # Apply Gaussian blur for feathering
        if feather_radius > 0:
            mask_blurred = cv2.GaussianBlur(mask_np, (feather_radius*2+1, feather_radius*2+1), 0)
            mask = Image.fromarray(mask_blurred)
        
        # Apply alpha matting for better hair/fur handling
        return self.apply_alpha_matting(image, mask)
    
    def apply_alpha_matting(self, image, mask):
        """Apply alpha matting for better edge quality"""
        # Convert to numpy arrays
        img_np = np.array(image)
        mask_np = np.array(mask)
        
        # Normalize mask
        if mask_np.max() > 1:
            mask_np = mask_np / 255.0
        
        # Create trimap (known foreground, known background, unknown)
        trimap = np.zeros_like(mask_np)
        trimap[mask_np > 0.8] = 255  # Definite foreground
        trimap[mask_np < 0.2] = 0    # Definite background
        trimap[(mask_np >= 0.2) & (mask_np <= 0.8)] = 128  # Unknown
        
        # For now, use the refined mask as alpha
        # In production, you might want to use a proper alpha matting algorithm
        alpha = mask_np
        
        # Apply alpha channel
        result = img_np.copy()
        if result.shape[-1] == 3:  # RGB
            result = np.dstack([result, (alpha * 255).astype(np.uint8)])
        else:  # Already has alpha
            result[:, :, 3] = (alpha * 255).astype(np.uint8)
        
        return Image.fromarray(result, 'RGBA')
    
    def remove_background_rmbg(self, image):
        """Remove background using RMBG-1.4 model"""
        try:
            # Preprocess
            inputs = self.rmbg_processor(image, return_tensors="pt").to(self.device)
            
            # Inference
            with torch.no_grad():
                outputs = self.rmbg_model(**inputs)
                logits = outputs.logits
            
            # Post-process
            mask = torch.sigmoid(logits).squeeze().cpu().numpy()
            mask = (mask * 255).astype(np.uint8)
            mask_pil = Image.fromarray(mask, 'L')
            
            return mask_pil
            
        except Exception as e:
            logger.error(f"RMBG model error: {e}")
            return None
    
    def remove_background_rembg(self, image):
        """Remove background using rembg (fallback)"""
        try:
            # Convert PIL to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            
            # Remove background
            result = remove(img_byte_arr, session=self.rembg_session)
            
            # Convert back to PIL
            return Image.open(io.BytesIO(result))
            
        except Exception as e:
            logger.error(f"Rembg error: {e}")
            return None
    
    def process_image(self, image, method='auto', feather_radius=2, enhance_edges=True):
        """Main processing function"""
        start_time = time.time()
        
        # Preprocess
        original_size = image.size
        image = self.preprocess_image(image)
        
        result = None
        
        # Try RMBG-1.4 first (best quality)
        if method in ['auto', 'rmbg'] and self.rmbg_model is not None:
            logger.info("Using RMBG-1.4 model")
            mask = self.remove_background_rmbg(image)
            if mask is not None:
                # Create result with transparency
                result = Image.new('RGBA', image.size, (0, 0, 0, 0))
                # Resize mask to match image if needed
                if mask.size != image.size:
                    mask = mask.resize(image.size, Image.Resampling.LANCZOS)
                
                # Apply mask
                image_rgba = image.convert('RGBA')
                result.paste(image_rgba, (0, 0))
                result.putalpha(mask)
                
                # Enhance edges if requested
                if enhance_edges:
                    result = self.enhance_edges(image, mask, feather_radius)
        
        # Fallback to rembg
        if result is None and method in ['auto', 'rembg']:
            logger.info("Using rembg u2net model")
            result = self.remove_background_rembg(image)
        
        # Resize back to original size if needed
        if result is not None and result.size != original_size:
            result = result.resize(original_size, Image.Resampling.LANCZOS)
        
        processing_time = time.time() - start_time
        logger.info(f"Processing completed in {processing_time:.2f} seconds")
        
        return result

# Initialize background remover
bg_remover = BackgroundRemover()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'device': bg_remover.device,
        'models_loaded': bg_remover.rmbg_model is not None
    })

@app.route('/api/remove-background', methods=['POST'])
def remove_background():
    """Main background removal endpoint"""
    try:
        # Check if file is present
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not supported'}), 400
        
        # Get processing options
        method = request.form.get('method', 'auto')
        feather_radius = int(request.form.get('feather_radius', 2))
        enhance_edges = request.form.get('enhance_edges', 'true').lower() == 'true'
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        filename = secure_filename(f"{file_id}.{file.filename.rsplit('.', 1)[1].lower()}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Save uploaded file
        file.save(filepath)
        
        try:
            # Load and process image
            image = Image.open(filepath)
            result = bg_remover.process_image(
                image, 
                method=method,
                feather_radius=feather_radius,
                enhance_edges=enhance_edges
            )
            
            if result is None:
                return jsonify({'error': 'Failed to process image'}), 500
            
            # Save result
            result_filename = f"{file_id}_result.png"
            result_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)
            result.save(result_path, 'PNG', optimize=True)
            
            # Return result info
            return jsonify({
                'success': True,
                'result_id': file_id,
                'download_url': f'/api/download/{file_id}',
                'original_size': image.size,
                'result_size': result.size
            })
            
        finally:
            # Clean up uploaded file
            if os.path.exists(filepath):
                os.remove(filepath)
    
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/download/<file_id>', methods=['GET'])
def download_result(file_id):
    """Download processed image"""
    try:
        result_filename = f"{file_id}_result.png"
        result_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)
        
        if not os.path.exists(result_path):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(
            result_path,
            as_attachment=True,
            download_name=f"no_background_{file_id}.png",
            mimetype='image/png'
        )
    
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/cleanup', methods=['POST'])
def cleanup_files():
    """Cleanup old temporary files"""
    try:
        current_time = time.time()
        max_age = 3600  # 1 hour
        
        for folder in [app.config['UPLOAD_FOLDER'], app.config['RESULT_FOLDER']]:
            for filename in os.listdir(folder):
                filepath = os.path.join(folder, filename)
                if os.path.isfile(filepath):
                    file_age = current_time - os.path.getctime(filepath)
                    if file_age > max_age:
                        os.remove(filepath)
        
        return jsonify({'success': True, 'message': 'Cleanup completed'})
    
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        return jsonify({'error': 'Cleanup failed'}), 500

# Automatic cleanup every hour
def periodic_cleanup():
    while True:
        time.sleep(3600)  # 1 hour
        try:
            cleanup_files()
        except:
            pass

cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
cleanup_thread.start()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)