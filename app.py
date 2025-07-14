from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import torch
import torchvision.transforms as transforms
from PIL import Image, ImageFilter
import numpy as np
import cv2
import io
import base64
import os
import time
from rembg import remove, new_session
import requests
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# Initialize models
try:
    rembg_session = new_session('u2net')  # Options: u2net, isnet-general-use, silueta
    print("✅ REMBG model loaded successfully")
except Exception as e:
    print(f"❌ Failed to load REMBG model: {e}")
    rembg_session = None

class BackgroundRemover:
    def __init__(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"🚀 Using device: {self.device}")
        
    def allowed_file(self, filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
    def validate_image(self, file_path):
        """Validate image format and size"""
        try:
            with Image.open(file_path) as img:
                # Check dimensions
                if img.width > 4000 or img.height > 4000:
                    return False, "Image too large (max 4000x4000)"
                if img.width < 100 or img.height < 100:
                    return False, "Image too small (min 100x100)"
                return True, "Valid"
        except Exception as e:
            return False, f"Invalid image: {str(e)}"
    
    def preprocess_image(self, image_path, target_size=None):
        """Preprocess image for optimal model performance"""
        image = Image.open(image_path).convert('RGB')
        
        # Store original size for later restoration
        original_size = image.size
        
        # Resize for processing if needed
        if target_size:
            # Maintain aspect ratio
            image.thumbnail(target_size, Image.Resampling.LANCZOS)
        
        return image, original_size
    
    def remove_background_rembg(self, image_path, model_name='u2net'):
        """Remove background using REMBG library"""
        try:
            with open(image_path, 'rb') as input_file:
                input_data = input_file.read()
            
            # Use specific model
            session = new_session(model_name)
            output_data = remove(input_data, session=session)
            
            # Convert to PIL Image
            output_image = Image.open(io.BytesIO(output_data))
            
            return output_image, True, "Success"
        except Exception as e:
            return None, False, f"REMBG processing failed: {str(e)}"
    
    def remove_background_bria_api(self, image_path, api_key):
        """Remove background using Bria API (if API key provided)"""
        try:
            url = "https://api.bria.ai/v1/background/remove"
            
            with open(image_path, 'rb') as f:
                files = {'image': f}
                headers = {'Authorization': f'Bearer {api_key}'}
                
                response = requests.post(url, files=files, headers=headers, timeout=60)
                
            if response.status_code == 200:
                output_image = Image.open(io.BytesIO(response.content))
                return output_image, True, "Success"
            else:
                return None, False, f"API Error: {response.status_code}"
        except Exception as e:
            return None, False, f"API processing failed: {str(e)}"
    
    def refine_edges(self, image, feather_radius=2):
        """Refine edges to reduce artifacts"""
        if feather_radius == 0:
            return image
            
        # Convert to numpy array
        img_array = np.array(image)
        
        if len(img_array.shape) == 4:  # RGBA
            alpha = img_array[:, :, 3]
            
            # Apply gaussian blur to alpha channel for soft edges
            alpha_blurred = cv2.GaussianBlur(alpha, (feather_radius*2+1, feather_radius*2+1), 0)
            
            # Create new image with refined alpha
            img_array[:, :, 3] = alpha_blurred
            
            return Image.fromarray(img_array, 'RGBA')
        
        return image
    
    def add_custom_background(self, foreground_image, background_color=None, background_image=None):
        """Add custom background to the processed image"""
        if background_image:
            # Resize background to match foreground
            bg = Image.open(background_image).convert('RGB')
            bg = bg.resize(foreground_image.size, Image.Resampling.LANCZOS)
        elif background_color:
            # Create solid color background
            bg = Image.new('RGB', foreground_image.size, background_color)
        else:
            # Return original with transparent background
            return foreground_image
        
        # Composite images
        if foreground_image.mode == 'RGBA':
            result = Image.alpha_composite(bg.convert('RGBA'), foreground_image)
        else:
            result = foreground_image
        
        return result

# Initialize background remover
bg_remover = BackgroundRemover()

@app.route('/')
def index():
    """Serve the main page"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Background Remover</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .upload-area { border: 2px dashed #ccc; border-radius: 10px; padding: 40px; text-align: center; margin: 20px 0; }
            .upload-area:hover { border-color: #007bff; background: #f8f9fa; }
            .result { margin-top: 30px; text-align: center; }
            .result img { max-width: 100%; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .btn { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
            .btn:hover { background: #0056b3; }
            .settings { background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }
            .error { background: #f8d7da; color: #721c24; padding: 15px; border-radius: 5px; margin: 10px 0; }
            .success { background: #d4edda; color: #155724; padding: 15px; border-radius: 5px; margin: 10px 0; }
        </style>
    </head>
    <body>
        <h1>🎨 AI Background Remover</h1>
        <p>Upload an image and let AI remove the background automatically!</p>
        
        <div class="settings">
            <h3>Settings</h3>
            <label>Model:</label>
            <select id="model">
                <option value="u2net">U2-Net (Free, Good Quality)</option>
                <option value="isnet-general-use">IS-Net (Free, Better Quality)</option>
                <option value="bria">Bria RMBG 2.0 (Requires API Key)</option>
            </select>
            <br><br>
            <label>Edge Feathering:</label>
            <input type="range" id="feather" min="0" max="10" value="2">
            <span id="featherValue">2px</span>
            <br><br>
            <div id="apiKeyDiv" style="display:none;">
                <label>Bria API Key:</label>
                <input type="password" id="apiKey" placeholder="Enter your Bria API key">
            </div>
        </div>
        
        <div class="upload-area" onclick="document.getElementById('fileInput').click()">
            <input type="file" id="fileInput" accept="image/*" style="display:none;">
            <h3>📸 Click to Upload Image</h3>
            <p>Supports PNG, JPG, JPEG (max 10MB)</p>
        </div>
        
        <button class="btn" onclick="processImage()" id="processBtn" disabled>Remove Background</button>
        
        <div id="result" class="result" style="display:none;">
            <h3>Result:</h3>
            <img id="resultImage" alt="Processed image">
            <br><br>
            <button class="btn" onclick="downloadImage()">📥 Download PNG</button>
            <button class="btn" onclick="resetAll()">🔄 Start Over</button>
        </div>
        
        <script>
            let selectedFile = null;
            let processedImageData = null;
            
            document.getElementById('fileInput').addEventListener('change', function(e) {
                const file = e.target.files[0];
                if (file) {
                    if (file.size > 10 * 1024 * 1024) {
                        showMessage('File too large. Maximum size is 10MB.', 'error');
                        return;
                    }
                    selectedFile = file;
                    document.getElementById('processBtn').disabled = false;
                    showMessage('Image selected: ' + file.name, 'success');
                }
            });
            
            document.getElementById('model').addEventListener('change', function(e) {
                const apiKeyDiv = document.getElementById('apiKeyDiv');
                if (e.target.value === 'bria') {
                    apiKeyDiv.style.display = 'block';
                } else {
                    apiKeyDiv.style.display = 'none';
                }
            });
            
            document.getElementById('feather').addEventListener('input', function(e) {
                document.getElementById('featherValue').textContent = e.target.value + 'px';
            });
            
            async function processImage() {
                if (!selectedFile) return;
                
                const btn = document.getElementById('processBtn');
                btn.disabled = true;
                btn.textContent = 'Processing...';
                
                const formData = new FormData();
                formData.append('image', selectedFile);
                formData.append('model', document.getElementById('model').value);
                formData.append('feather', document.getElementById('feather').value);
                
                const apiKey = document.getElementById('apiKey').value;
                if (apiKey) {
                    formData.append('api_key', apiKey);
                }
                
                try {
                    const response = await fetch('/api/remove-background', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        processedImageData = result.image;
                        document.getElementById('resultImage').src = result.image;
                        document.getElementById('result').style.display = 'block';
                        showMessage('Background removed successfully!', 'success');
                    } else {
                        showMessage('Error: ' + result.error, 'error');
                    }
                } catch (error) {
                    showMessage('Network error: ' + error.message, 'error');
                } finally {
                    btn.disabled = false;
                    btn.textContent = 'Remove Background';
                }
            }
            
            function downloadImage() {
                if (!processedImageData) return;
                
                const link = document.createElement('a');
                link.href = processedImageData;
                link.download = 'background_removed_' + Date.now() + '.png';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            }
            
            function resetAll() {
                selectedFile = null;
                processedImageData = null;
                document.getElementById('fileInput').value = '';
                document.getElementById('processBtn').disabled = true;
                document.getElementById('result').style.display = 'none';
                clearMessages();
            }
            
            function showMessage(message, type) {
                clearMessages();
                const div = document.createElement('div');
                div.className = type;
                div.textContent = message;
                document.body.appendChild(div);
            }
            
            function clearMessages() {
                const messages = document.querySelectorAll('.error, .success');
                messages.forEach(msg => msg.remove());
            }
        </script>
    </body>
    </html>
    '''

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy', 
        'device': str(bg_remover.device),
        'models_available': rembg_session is not None
    })

@app.route('/api/remove-background', methods=['POST'])
def remove_background():
    try:
        # Check if file is present
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not bg_remover.allowed_file(file.filename):
            return jsonify({'error': 'Invalid file format. Use PNG, JPG, or JPEG'}), 400
        
        # Get processing options
        model_type = request.form.get('model', 'u2net')  # u2net, isnet-general-use, u2netp
        feather_radius = int(request.form.get('feather', 2))
        api_key = request.form.get('api_key', '')  # For Bria API
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        timestamp = str(int(time.time()))
        unique_filename = f"{timestamp}_{filename}"
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(file_path)
        
        # Validate image
        is_valid, validation_msg = bg_remover.validate_image(file_path)
        if not is_valid:
            os.remove(file_path)
            return jsonify({'error': validation_msg}), 400
        
        # Process image based on selected method
        if api_key and model_type == 'bria':
            result_image, success, message = bg_remover.remove_background_bria_api(file_path, api_key)
        else:
            result_image, success, message = bg_remover.remove_background_rembg(file_path, model_type)
        
        if not success:
            os.remove(file_path)
            return jsonify({'error': message}), 500
        
        # Refine edges
        result_image = bg_remover.refine_edges(result_image, feather_radius)
        
        # Save processed image
        output_filename = f"processed_{unique_filename.rsplit('.', 1)[0]}.png"
        output_path = os.path.join(PROCESSED_FOLDER, output_filename)
        result_image.save(output_path, format='PNG')
        
        # Convert to base64 for response
        buffer = io.BytesIO()
        result_image.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        # Cleanup original file
        os.remove(file_path)
        
        return jsonify({
            'success': True,
            'image': f"data:image/png;base64,{img_base64}",
            'filename': output_filename,
            'message': 'Background removed successfully'
        })
        
    except Exception as e:
        # Cleanup file on error
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    """Download processed image"""
    try:
        file_path = os.path.join(PROCESSED_FOLDER, secure_filename(filename))
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/edit-mask', methods=['POST'])
def edit_mask():
    """Allow users to manually edit the mask"""
    try:
        data = request.get_json()
        
        # Get base64 image and edit coordinates
        image_data = data.get('image')
        edits = data.get('edits', [])  # Array of {x, y, radius, action: 'add'/'remove'}
        
        # Decode image
        image_bytes = base64.b64decode(image_data.split(',')[1])
        image = Image.open(io.BytesIO(image_bytes))
        
        # Apply edits to alpha channel
        img_array = np.array(image)
        
        if len(img_array.shape) == 4:  # RGBA
            for edit in edits:
                x, y, radius = edit['x'], edit['y'], edit['radius']
                action = edit['action']
                
                # Create circular mask
                y_coords, x_coords = np.ogrid[:img_array.shape[0], :img_array.shape[1]]
                mask = (x_coords - x) ** 2 + (y_coords - y) ** 2 <= radius ** 2
                
                if action == 'add':
                    img_array[mask, 3] = 255  # Restore area
                elif action == 'remove':
                    img_array[mask, 3] = 0    # Remove area
        
        # Convert back to image
        edited_image = Image.fromarray(img_array, 'RGBA')
        
        # Convert to base64
        buffer = io.BytesIO()
        edited_image.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return jsonify({
            'success': True,
            'image': f"data:image/png;base64,{img_base64}"
        })
        
    except Exception as e:
        return jsonify({'error': f'Edit failed: {str(e)}'}), 500

if __name__ == '__main__':
    print("🚀 Starting AI Background Removal Server...")
    print("📱 Open http://localhost:5000 in your browser")
    print("🔍 API Health Check: http://localhost:5000/api/health")
    app.run(debug=True, host='0.0.0.0', port=5000)