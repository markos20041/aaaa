from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import io
import base64
import numpy as np
from PIL import Image, ImageFilter
import cv2
from rembg import new_session, remove
import torch
from werkzeug.utils import secure_filename
import os
import tempfile
import time
from skimage import morphology
from threading import Lock

app = Flask(__name__)
CORS(app)

# Configure upload settings
UPLOAD_FOLDER = 'uploads'
RESULT_FOLDER = 'results'
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

# Create directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

# Model sessions cache
model_sessions = {}
model_lock = Lock()

class BackgroundRemover:
    def __init__(self):
        self.supported_models = {
            'u2net': 'u2net',
            'u2net_human_seg': 'u2net_human_seg',
            'silueta': 'silueta',
            'isnet-general-use': 'isnet-general-use'
        }
    
    def get_model_session(self, model_name='u2net'):
        """Get or create model session with thread safety"""
        with model_lock:
            if model_name not in model_sessions:
                print(f"Loading model: {model_name}")
                model_sessions[model_name] = new_session(model_name)
            return model_sessions[model_name]
    
    def preprocess_image(self, image, max_size=1024):
        """Preprocess image for optimal results"""
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize if too large (maintain aspect ratio)
        width, height = image.size
        if max(width, height) > max_size:
            ratio = max_size / max(width, height)
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return image
    
    def enhance_edges(self, mask, original_size):
        """Enhance mask edges for better hair and detail preservation"""
        # Convert PIL mask to numpy
        mask_np = np.array(mask.resize(original_size, Image.Resampling.LANCZOS))
        
        # Apply morphological operations to clean up the mask
        mask_np = morphology.closing(mask_np > 128, morphology.disk(2))
        mask_np = morphology.opening(mask_np, morphology.disk(1))
        
        # Apply Gaussian blur for softer edges
        mask_np = mask_np.astype(np.uint8) * 255
        mask_np = cv2.GaussianBlur(mask_np, (3, 3), 1)
        
        return Image.fromarray(mask_np)
    
    def apply_alpha_matting(self, image, mask, trimap_erosion=10, trimap_dilation=20):
        """Apply alpha matting for better edge quality"""
        try:
            import cv2
            
            # Convert images to numpy arrays
            img_np = np.array(image)
            mask_np = np.array(mask.convert('L'))
            
            # Create trimap
            trimap = np.zeros_like(mask_np)
            
            # Erode mask for definite foreground
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (trimap_erosion, trimap_erosion))
            fg_mask = cv2.erode(mask_np, kernel, iterations=1)
            trimap[fg_mask > 200] = 255  # Definite foreground
            
            # Dilate mask for definite background
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (trimap_dilation, trimap_dilation))
            bg_mask = cv2.dilate(mask_np, kernel, iterations=1)
            trimap[bg_mask < 50] = 0  # Definite background
            
            # Unknown region
            trimap[(trimap != 0) & (trimap != 255)] = 128
            
            # Apply guided filter or simple feathering as fallback
            mask_refined = cv2.GaussianBlur(mask_np, (5, 5), 2)
            
            return Image.fromarray(mask_refined)
            
        except Exception as e:
            print(f"Alpha matting failed, using original mask: {e}")
            return mask
    
    def remove_background(self, image, model_name='u2net', enhance_edges=True, alpha_matting=False):
        """Main background removal function"""
        original_size = image.size
        
        # Preprocess image
        processed_image = self.preprocess_image(image)
        
        # Get model session
        session = self.get_model_session(model_name)
        
        # Remove background
        result = remove(processed_image, session=session)
        
        # Extract mask from result
        mask = result.split()[-1] if len(result.split()) == 4 else None
        
        if mask:
            # Enhance edges if requested
            if enhance_edges:
                mask = self.enhance_edges(mask, original_size)
            
            # Apply alpha matting if requested
            if alpha_matting:
                mask = self.apply_alpha_matting(image, mask)
            
            # Apply mask to original image
            image_resized = image.resize(mask.size, Image.Resampling.LANCZOS)
            final_result = Image.new('RGBA', image_resized.size, (0, 0, 0, 0))
            final_result.paste(image_resized, mask=mask)
            
            return final_result
        else:
            # Fallback: return the rembg result directly
            return result.resize(original_size, Image.Resampling.LANCZOS)

# Initialize background remover
bg_remover = BackgroundRemover()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'models': list(bg_remover.supported_models.keys())})

@app.route('/api/remove-background', methods=['POST'])
def remove_background_api():
    try:
        start_time = time.time()
        
        # Check if file is present
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not supported. Use PNG, JPG, JPEG, or WEBP'}), 400
        
        # Get parameters
        model_name = request.form.get('model', 'u2net')
        enhance_edges = request.form.get('enhance_edges', 'true').lower() == 'true'
        alpha_matting = request.form.get('alpha_matting', 'false').lower() == 'true'
        
        if model_name not in bg_remover.supported_models:
            return jsonify({'error': f'Model {model_name} not supported'}), 400
        
        # Read and validate image
        try:
            image = Image.open(file.stream)
        except Exception as e:
            return jsonify({'error': f'Invalid image file: {str(e)}'}), 400
        
        # Process image
        try:
            result = bg_remover.remove_background(
                image, 
                model_name=model_name,
                enhance_edges=enhance_edges,
                alpha_matting=alpha_matting
            )
        except Exception as e:
            return jsonify({'error': f'Background removal failed: {str(e)}'}), 500
        
        # Convert result to base64
        img_buffer = io.BytesIO()
        result.save(img_buffer, format='PNG', optimize=True)
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
        
        processing_time = time.time() - start_time
        
        return jsonify({
            'success': True,
            'image': f'data:image/png;base64,{img_base64}',
            'processing_time': round(processing_time, 2),
            'model_used': model_name,
            'image_size': result.size
        })
        
    except Exception as e:
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/api/remove-background-file', methods=['POST'])
def remove_background_file():
    """Alternative endpoint that returns file for download"""
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        file = request.files['image']
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not supported'}), 400
        
        # Get parameters
        model_name = request.form.get('model', 'u2net')
        enhance_edges = request.form.get('enhance_edges', 'true').lower() == 'true'
        
        # Process image
        image = Image.open(file.stream)
        result = bg_remover.remove_background(image, model_name=model_name, enhance_edges=enhance_edges)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
            result.save(tmp_file.name, format='PNG')
            
            return send_file(
                tmp_file.name,
                as_attachment=True,
                download_name=f"removed_bg_{secure_filename(file.filename.rsplit('.', 1)[0])}.png",
                mimetype='image/png'
            )
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting Background Removal Server...")
    print("Available models:", list(bg_remover.supported_models.keys()))
    app.run(debug=True, host='0.0.0.0', port=5000)