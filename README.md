# AI-Powered Background Removal Tool

A professional-grade background removal application using state-of-the-art AI models including RMBG 2.0 and BiRefNet. This tool provides high-precision background removal with support for edge enhancement, batch processing, and manual mask refinement.

## 🚀 Features

- **State-of-the-Art Models**: RMBG 2.0 (BRIA AI) and BiRefNet support
- **High Precision**: Handles complex edges, hair, and semi-transparent areas
- **Edge Enhancement**: Advanced post-processing for natural-looking results
- **Batch Processing**: Process multiple images simultaneously
- **Manual Refinement**: Fine-tune masks with morphological operations
- **Modern UI**: Beautiful, responsive web interface
- **Multiple Formats**: Support for PNG, JPG input with PNG output
- **API Integration**: RESTful API for easy integration

## 📋 Model Recommendations

### 1. RMBG 2.0 (BRIA AI) - **RECOMMENDED**
- **Accuracy**: 90% success rate in benchmarks
- **Best For**: Professional use, e-commerce, high-quality results
- **Features**: Non-binary masks (256 levels of transparency)
- **License**: Commercial license required for commercial use
- **Performance**: ~1-2 seconds per image on RTX A4000

### 2. BiRefNet - **Open Source Alternative**
- **Accuracy**: 85% success rate in benchmarks  
- **Best For**: Open source projects, good balance of quality/performance
- **License**: Free for commercial use
- **Performance**: ~1-2 seconds per image on RTX A4000

### 3. Performance Comparison
| Model | Accuracy | Speed | License | Best Use Case |
|-------|----------|-------|---------|---------------|
| RMBG 2.0 | 90% | Fast | Commercial | Professional/Enterprise |
| BiRefNet | 85% | Fast | Open Source | General Purpose |

## 🛠 Installation & Setup

### Prerequisites
- Python 3.8 or higher
- CUDA-compatible GPU (recommended) or CPU
- 8GB+ RAM (16GB+ recommended for batch processing)

### Quick Start

1. **Clone the repository**
```bash
git clone <repository-url>
cd background-removal-tool
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Run the application**
```bash
python app.py
```

4. **Access the web interface**
Open `http://localhost:5000` in your browser

## 📊 Image Processing Workflow

```
Upload Image → Preprocessing → AI Model Inference → Post-processing → Output PNG
      ↓              ↓              ↓               ↓           ↓
   Validation    Resize/Norm    Generate Mask    Edge Enhancement  Transparent BG
```

### Detailed Processing Steps:

1. **Input Validation**: Check format, size limits (max 4000px)
2. **Preprocessing**: 
   - Convert to RGB
   - Resize to model input size (1024x1024)
   - Normalize with ImageNet stats
3. **AI Inference**: Generate segmentation mask
4. **Post-processing**:
   - Resize mask back to original dimensions
   - Apply edge enhancement (Gaussian blur)
   - Optional feathering for softer edges
5. **Output**: Apply mask to create transparent PNG

## 🎯 Handling Edge Cases

### Hair and Fine Details
```python
# Edge enhancement for hair and fine details
enhance_edges=True  # Applies slight Gaussian blur (radius=0.5)
```

### Soft Edges and Feathering
```python
# Feathering for softer transitions
feather_amount=1.5  # Range: 0-5, higher = softer edges
```

### Complex Backgrounds
- RMBG 2.0 excels at complex backgrounds (90% vs BiRefNet's 75%)
- Use morphological operations for mask refinement:
  - Dilate: Expand mask to include more pixels
  - Erode: Contract mask to remove noise

### Semi-transparent Areas
- Models output 256-level alpha masks (not binary)
- Preserves natural transparency in glass, fabric, etc.

## 🔧 API Integration

### Basic Usage
```python
import requests

# Single image processing
with open('image.jpg', 'rb') as f:
    response = requests.post(
        'http://localhost:5000/remove-background-json',
        files={'image': f},
        data={
            'model': 'rmbg2',
            'enhance_edges': 'true',
            'feather_amount': '1.0'
        }
    )

result = response.json()
if result['success']:
    # result['result_image'] contains base64 encoded PNG
    # result['mask'] contains base64 encoded mask
```

### JavaScript/Frontend Integration
```javascript
const formData = new FormData();
formData.append('image', imageFile);
formData.append('model', 'rmbg2');
formData.append('enhance_edges', 'true');

fetch('/remove-background-json', {
    method: 'POST',
    body: formData
})
.then(response => response.json())
.then(data => {
    if (data.success) {
        // Display result
        const img = document.createElement('img');
        img.src = `data:image/png;base64,${data.result_image}`;
    }
});
```

### Batch Processing
```python
files = [('images', open(f'image{i}.jpg', 'rb')) for i in range(1, 6)]
response = requests.post(
    'http://localhost:5000/batch-process',
    files=files,
    data={'model': 'rmbg2'}
)
```

## 🎨 Manual Mask Editing

The tool provides post-processing capabilities to refine masks:

### Morphological Operations
```python
# Expand mask (fill gaps)
dilate_iterations = 2

# Contract mask (remove noise)  
erode_iterations = 1

# Apply refinement
response = requests.post(
    'http://localhost:5000/refine-mask',
    files={'mask': mask_file},
    data={
        'dilate_iterations': dilate_iterations,
        'erode_iterations': erode_iterations
    }
)
```

### Frontend Controls
- **Expand Mask**: Fill gaps in hair, clothing details
- **Contract Mask**: Remove background noise, artifacts
- **Real-time Preview**: See changes before applying

## ⚡ Performance Optimization

### For High Volume Production

1. **GPU Optimization**
```python
# Use mixed precision for faster inference
torch.set_float32_matmul_precision('high')

# Batch processing for efficiency
# Process 4-8 images simultaneously
```

2. **Image Size Limits**
```python
# Implement intelligent resizing
max_size = 4000  # Prevent memory issues
if max(image.size) > max_size:
    ratio = max_size / max(image.size)
    new_size = tuple(int(dim * ratio) for dim in image.size)
    image = image.resize(new_size, Image.LANCZOS)
```

3. **Caching Strategy**
```python
# Cache model weights in memory
# Use Redis for result caching (optional)
# Implement CDN for static assets
```

4. **Scaling Recommendations**
- **Single Server**: Handles ~100-200 images/hour
- **Load Balancer**: Scale horizontally with multiple GPU instances
- **Queue System**: Use Celery/Redis for async processing
- **CDN**: Serve processed images from edge locations

### Memory Management
```python
# Clear GPU cache between batches
torch.cuda.empty_cache()

# Use streaming for large files
# Implement image compression for storage
```

## 🚀 Production Deployment

### Docker Deployment
```dockerfile
FROM pytorch/pytorch:2.0.0-cuda11.7-cudnn8-runtime

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--timeout", "300", "app:app"]
```

### Environment Variables
```bash
export FLASK_ENV=production
export MODEL_CACHE_DIR=/models
export MAX_IMAGE_SIZE=4000
export BATCH_SIZE_LIMIT=10
```

### Health Monitoring
```python
# Built-in health check endpoint
GET /health

# Returns:
{
  "status": "healthy",
  "available_models": ["rmbg2", "birefnet"],
  "device": "cuda:0"
}
```

## 📱 Mobile App Integration

### React Native Example
```javascript
const removeBackground = async (imageUri) => {
  const formData = new FormData();
  formData.append('image', {
    uri: imageUri,
    type: 'image/jpeg',
    name: 'image.jpg',
  });
  
  const response = await fetch(`${API_BASE}/remove-background-json`, {
    method: 'POST',
    body: formData,
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  
  return await response.json();
};
```

### iOS Swift Example
```swift
func removeBackground(image: UIImage, completion: @escaping (Result<Data, Error>) -> Void) {
    guard let imageData = image.jpegData(compressionQuality: 0.8) else { return }
    
    let url = URL(string: "\(apiBase)/remove-background")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    
    let boundary = UUID().uuidString
    request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
    
    // Create multipart body...
    URLSession.shared.dataTask(with: request) { data, response, error in
        // Handle response...
    }.resume()
}
```

## 🔒 Security Considerations

### Input Validation
- File size limits (default: 20MB)
- Format validation (PNG, JPG, JPEG)
- MIME type checking
- Image dimension limits

### Rate Limiting
```python
from flask_limiter import Limiter

limiter = Limiter(
    app,
    key_func=lambda: request.remote_addr,
    default_limits=["100 per hour"]
)

@app.route('/remove-background')
@limiter.limit("10 per minute")
def remove_background():
    # ...
```

### Data Privacy
- No image storage by default
- Optional secure temporary storage
- GDPR compliance considerations
- User consent for processing

## 🧪 Testing

### Unit Tests
```bash
python -m pytest tests/
```

### Performance Testing
```bash
# Load testing with locust
pip install locust
locust -f tests/load_test.py
```

### Quality Assurance
```python
# Test with various image types
test_images = [
    "portrait_with_hair.jpg",
    "product_on_transparent.png", 
    "complex_background.jpg",
    "semi_transparent_object.png"
]
```

## 📞 Support & Troubleshooting

### Common Issues

1. **CUDA Out of Memory**
   - Reduce batch size
   - Lower image resolution
   - Use CPU mode: `device='cpu'`

2. **Model Loading Fails**
   - Check internet connection
   - Verify HuggingFace access
   - Clear model cache

3. **Poor Results on Hair**
   - Enable edge enhancement
   - Increase feather amount
   - Try manual mask refinement

### Getting Help
- Check logs: `tail -f app.log`
- Monitor GPU usage: `nvidia-smi`
- Test with sample images provided

## 📜 License & Commercial Use

### RMBG 2.0 (BRIA AI)
- **Non-commercial**: Free use
- **Commercial**: License required from BRIA AI
- **Contact**: [BRIA AI Commercial License](https://bria.ai/rmbg-for-commercial-use)

### BiRefNet
- **License**: Open source (MIT-style)
- **Commercial Use**: Permitted
- **Attribution**: Required

### This Tool
- **License**: MIT (for the application code)
- **Model Licenses**: Governed by respective model licenses
- **Disclaimer**: Users responsible for compliance with model licenses

## 🔮 Future Enhancements

- [ ] Video background removal
- [ ] Real-time webcam processing  
- [ ] Custom model fine-tuning
- [ ] Advanced editing tools (inpainting)
- [ ] Cloud storage integration
- [ ] Webhook notifications
- [ ] A/B testing framework

---

**Built with ❤️ for professional background removal needs**