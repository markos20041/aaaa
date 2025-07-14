import os
import io
import uuid
import time
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image
import numpy as np
from rembg import remove, new_session
import logging
from werkzeug.utils import secure_filename
import threading

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

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'bmp', 'tiff'}

class BackgroundRemover:
    def __init__(self):
        logger.info("Initializing Background Remover...")
        try:
            # Load rembg session
            logger.info("Loading U2Net model...")
            self.rembg_session = new_session('u2net')
            logger.info("Background remover initialized successfully!")
        except Exception as e:
            logger.error(f"Error initializing background remover: {e}")
            self.rembg_session = None
    
    def preprocess_image(self, image):
        """Preprocess image for optimal results"""
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize if too large (for performance)
        max_size = 1024
        if max(image.size) > max_size:
            ratio = max_size / max(image.size)
            new_size = tuple(int(dim * ratio) for dim in image.size)
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        return image
    
    def remove_background(self, image):
        """Remove background using rembg"""
        try:
            # Convert PIL to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            
            # Remove background
            if self.rembg_session:
                result = remove(img_byte_arr, session=self.rembg_session)
            else:
                result = remove(img_byte_arr)
            
            # Convert back to PIL
            result_image = Image.open(io.BytesIO(result))
            return result_image
            
        except Exception as e:
            logger.error(f"Background removal error: {e}")
            return None
    
    def process_image(self, image):
        """Main processing function"""
        start_time = time.time()
        
        # Store original size
        original_size = image.size
        
        # Preprocess
        image = self.preprocess_image(image)
        
        # Remove background
        result = self.remove_background(image)
        
        # Resize back to original size if needed
        if result and result.size != original_size:
            result = result.resize(original_size, Image.Resampling.LANCZOS)
        
        processing_time = time.time() - start_time
        logger.info(f"Processing completed in {processing_time:.2f} seconds")
        
        return result

# Initialize background remover
bg_remover = BackgroundRemover()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Serve the main page"""
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "Frontend not found. Please make sure index.html exists."

@app.route('/style.css')
def css():
    """Serve CSS file"""
    try:
        with open('style.css', 'r', encoding='utf-8') as f:
            response = app.response_class(f.read(), mimetype='text/css')
            return response
    except FileNotFoundError:
        return "CSS file not found"

@app.route('/script.js')
def js():
    """Serve JavaScript file"""
    try:
        with open('script.js', 'r', encoding='utf-8') as f:
            response = app.response_class(f.read(), mimetype='application/javascript')
            return response
    except FileNotFoundError:
        return "JavaScript file not found"

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'models_loaded': bg_remover.rembg_session is not None,
        'message': 'Background removal service is running'
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
            return jsonify({'error': 'File type not supported. Please use PNG, JPG, or WEBP.'}), 400
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        filename = secure_filename(f"{file_id}.{file.filename.rsplit('.', 1)[1].lower()}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Save uploaded file
        file.save(filepath)
        
        try:
            # Load and process image
            image = Image.open(filepath)
            logger.info(f"Processing image: {image.size} pixels")
            
            result = bg_remover.process_image(image)
            
            if result is None:
                return jsonify({'error': 'Failed to process image. Please try again.'}), 500
            
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
                'result_size': result.size,
                'message': 'Background removed successfully!'
            })
            
        finally:
            # Clean up uploaded file
            if os.path.exists(filepath):
                os.remove(filepath)
    
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/api/download/<file_id>', methods=['GET'])
def download_result(file_id):
    """Download processed image"""
    try:
        result_filename = f"{file_id}_result.png"
        result_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)
        
        if not os.path.exists(result_path):
            return jsonify({'error': 'File not found or expired'}), 404
        
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
        cleaned_count = 0
        
        for folder in [app.config['RESULT_FOLDER']]:
            if os.path.exists(folder):
                for filename in os.listdir(folder):
                    filepath = os.path.join(folder, filename)
                    if os.path.isfile(filepath):
                        file_age = current_time - os.path.getctime(filepath)
                        if file_age > max_age:
                            os.remove(filepath)
                            cleaned_count += 1
        
        return jsonify({
            'success': True, 
            'message': f'Cleanup completed. Removed {cleaned_count} files.'
        })
    
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        return jsonify({'error': 'Cleanup failed'}), 500

# Automatic cleanup every hour
def periodic_cleanup():
    while True:
        time.sleep(3600)  # 1 hour
        try:
            with app.app_context():
                cleanup_files()
        except:
            pass

cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
cleanup_thread.start()

if __name__ == '__main__':
    print("🚀 Starting Background Removal Server...")
    print("🌐 Server will be available at: http://localhost:5000")
    print("📖 API Documentation:")
    print("   - GET  /api/health              - Check server health")
    print("   - POST /api/remove-background   - Remove background from image")
    print("   - GET  /api/download/<id>       - Download processed image")
    print("   - POST /api/cleanup             - Clean temporary files")
    
    app.run(debug=True, host='0.0.0.0', port=5000)