import os
import io
import base64
import time
from PIL import Image, ImageFilter
import numpy as np
import cv2
import torch
import torchvision.transforms as transforms
from transformers import AutoModelForImageSegmentation
from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

class BackgroundRemover:
    def __init__(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.models = {}
        self.load_models()
        
    def load_models(self):
        """Load available background removal models"""
        try:
            # RMBG 2.0 (BRIA AI) - State-of-the-art
            logger.info("Loading RMBG 2.0 model...")
            self.models['rmbg2'] = AutoModelForImageSegmentation.from_pretrained(
                'briaai/RMBG-2.0', 
                trust_remote_code=True,
                torch_dtype=torch.float32
            )
            self.models['rmbg2'].to(self.device)
            self.models['rmbg2'].eval()
            logger.info("RMBG 2.0 loaded successfully")
            
        except Exception as e:
            logger.warning(f"Could not load RMBG 2.0: {e}")
            
        try:
            # BiRefNet - Open source alternative
            logger.info("Loading BiRefNet model...")
            self.models['birefnet'] = AutoModelForImageSegmentation.from_pretrained(
                'ZhengPeng7/BiRefNet',
                trust_remote_code=True,
                torch_dtype=torch.float32
            )
            self.models['birefnet'].to(self.device)
            self.models['birefnet'].eval()
            logger.info("BiRefNet loaded successfully")
            
        except Exception as e:
            logger.warning(f"Could not load BiRefNet: {e}")

    def preprocess_image(self, image, target_size=(1024, 1024)):
        """Preprocess image for model input"""
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
            
        # Store original size for later restoration
        original_size = image.size
        
        # Resize image
        image_resized = image.resize(target_size, Image.LANCZOS)
        
        # Transform for model input
        transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])
        
        input_tensor = transform(image_resized).unsqueeze(0).to(self.device)
        
        return input_tensor, original_size, image_resized

    def postprocess_mask(self, mask, original_size, enhance_edges=True, feather_amount=0):
        """Post-process the generated mask"""
        # Convert to PIL Image
        mask_array = (mask.cpu().numpy() * 255).astype(np.uint8)
        mask_pil = Image.fromarray(mask_array, mode='L')
        
        # Resize back to original size
        mask_pil = mask_pil.resize(original_size, Image.LANCZOS)
        
        if enhance_edges:
            # Apply slight blur to soften edges (handles hair and soft edges)
            mask_pil = mask_pil.filter(ImageFilter.GaussianBlur(radius=0.5))
            
        if feather_amount > 0:
            # Apply feathering for softer edges
            mask_pil = mask_pil.filter(ImageFilter.GaussianBlur(radius=feather_amount))
            
        return mask_pil

    def remove_background(self, image, model_name='rmbg2', enhance_edges=True, feather_amount=0):
        """Remove background from image"""
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not available. Available: {list(self.models.keys())}")
            
        model = self.models[model_name]
        
        # Preprocess image
        input_tensor, original_size, resized_image = self.preprocess_image(image)
        
        # Generate mask
        with torch.no_grad():
            if model_name == 'rmbg2':
                prediction = model(input_tensor)[-1].sigmoid()
            else:
                prediction = model(input_tensor)[-1].sigmoid()
                
        mask = prediction[0].squeeze()
        
        # Post-process mask
        mask_pil = self.postprocess_mask(mask, original_size, enhance_edges, feather_amount)
        
        # Apply mask to original image
        image_rgba = image.convert('RGBA')
        image_rgba.putalpha(mask_pil)
        
        return image_rgba, mask_pil

    def refine_mask(self, mask, dilate_iterations=1, erode_iterations=1):
        """Refine mask using morphological operations"""
        mask_array = np.array(mask)
        
        # Create kernel for morphological operations
        kernel = np.ones((3, 3), np.uint8)
        
        # Apply dilation to fill gaps
        if dilate_iterations > 0:
            mask_array = cv2.dilate(mask_array, kernel, iterations=dilate_iterations)
            
        # Apply erosion to smooth edges
        if erode_iterations > 0:
            mask_array = cv2.erode(mask_array, kernel, iterations=erode_iterations)
            
        return Image.fromarray(mask_array, mode='L')

# Initialize the background remover
bg_remover = BackgroundRemover()

@app.route('/', methods=['GET'])
def index():
    """Serve the main frontend interface"""
    return render_template('index.html')

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'available_models': list(bg_remover.models.keys()),
        'device': str(bg_remover.device)
    })

@app.route('/remove-background', methods=['POST'])
def remove_background_endpoint():
    """Main background removal endpoint"""
    try:
        start_time = time.time()
        
        # Get parameters
        model_name = request.form.get('model', 'rmbg2')
        enhance_edges = request.form.get('enhance_edges', 'true').lower() == 'true'
        feather_amount = float(request.form.get('feather_amount', '0'))
        output_format = request.form.get('output_format', 'png').lower()
        
        # Get image
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
            
        image_file = request.files['image']
        if image_file.filename == '':
            return jsonify({'error': 'No image selected'}), 400
            
        # Load and process image
        image = Image.open(image_file.stream)
        
        # Validate image size (prevent memory issues)
        max_size = 4000
        if max(image.size) > max_size:
            ratio = max_size / max(image.size)
            new_size = tuple(int(dim * ratio) for dim in image.size)
            image = image.resize(new_size, Image.LANCZOS)
            
        # Remove background
        result_image, mask = bg_remover.remove_background(
            image, 
            model_name=model_name,
            enhance_edges=enhance_edges,
            feather_amount=feather_amount
        )
        
        # Prepare response
        processing_time = time.time() - start_time
        
        # Convert to bytes
        img_buffer = io.BytesIO()
        result_image.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        return send_file(
            img_buffer,
            mimetype='image/png',
            as_attachment=True,
            download_name=f'no_bg_{int(time.time())}.png'
        )
        
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/remove-background-json', methods=['POST'])
def remove_background_json():
    """Background removal endpoint returning JSON with base64 encoded result"""
    try:
        start_time = time.time()
        
        # Get parameters
        data = request.get_json() if request.is_json else request.form
        model_name = data.get('model', 'rmbg2')
        enhance_edges = str(data.get('enhance_edges', 'true')).lower() == 'true'
        feather_amount = float(data.get('feather_amount', '0'))
        
        # Get image (base64 or file upload)
        if request.is_json:
            if 'image_base64' not in data:
                return jsonify({'error': 'No image_base64 provided'}), 400
            image_data = base64.b64decode(data['image_base64'])
            image = Image.open(io.BytesIO(image_data))
        else:
            if 'image' not in request.files:
                return jsonify({'error': 'No image provided'}), 400
            image = Image.open(request.files['image'].stream)
            
        # Process image
        result_image, mask = bg_remover.remove_background(
            image,
            model_name=model_name,
            enhance_edges=enhance_edges,
            feather_amount=feather_amount
        )
        
        # Convert to base64
        img_buffer = io.BytesIO()
        result_image.save(img_buffer, format='PNG')
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        
        mask_buffer = io.BytesIO()
        mask.save(mask_buffer, format='PNG')
        mask_base64 = base64.b64encode(mask_buffer.getvalue()).decode()
        
        processing_time = time.time() - start_time
        
        return jsonify({
            'success': True,
            'result_image': img_base64,
            'mask': mask_base64,
            'processing_time': round(processing_time, 2),
            'model_used': model_name,
            'original_size': image.size
        })
        
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/refine-mask', methods=['POST'])
def refine_mask_endpoint():
    """Endpoint for manual mask refinement"""
    try:
        # Get parameters
        dilate_iterations = int(request.form.get('dilate_iterations', '1'))
        erode_iterations = int(request.form.get('erode_iterations', '1'))
        
        # Get mask image
        if 'mask' not in request.files:
            return jsonify({'error': 'No mask provided'}), 400
            
        mask_file = request.files['mask']
        mask = Image.open(mask_file.stream).convert('L')
        
        # Refine mask
        refined_mask = bg_remover.refine_mask(mask, dilate_iterations, erode_iterations)
        
        # Return refined mask
        mask_buffer = io.BytesIO()
        refined_mask.save(mask_buffer, format='PNG')
        mask_buffer.seek(0)
        
        return send_file(
            mask_buffer,
            mimetype='image/png',
            as_attachment=True,
            download_name=f'refined_mask_{int(time.time())}.png'
        )
        
    except Exception as e:
        logger.error(f"Error refining mask: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/batch-process', methods=['POST'])
def batch_process():
    """Batch processing endpoint for multiple images"""
    try:
        files = request.files.getlist('images')
        if not files:
            return jsonify({'error': 'No images provided'}), 400
            
        model_name = request.form.get('model', 'rmbg2')
        enhance_edges = request.form.get('enhance_edges', 'true').lower() == 'true'
        
        results = []
        
        for idx, file in enumerate(files):
            try:
                image = Image.open(file.stream)
                result_image, mask = bg_remover.remove_background(
                    image,
                    model_name=model_name,
                    enhance_edges=enhance_edges
                )
                
                # Convert to base64
                img_buffer = io.BytesIO()
                result_image.save(img_buffer, format='PNG')
                img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
                
                results.append({
                    'index': idx,
                    'filename': file.filename,
                    'success': True,
                    'result_image': img_base64
                })
                
            except Exception as e:
                results.append({
                    'index': idx,
                    'filename': file.filename,
                    'success': False,
                    'error': str(e)
                })
                
        return jsonify({
            'success': True,
            'results': results,
            'total_processed': len(results)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)