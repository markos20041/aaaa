# AI-Powered Background Removal Tool

A professional-grade web application that uses advanced AI models to automatically remove backgrounds from images with high precision. Built for e-commerce, profile pictures, and design assets.

## ✨ Features

- **AI-Powered Processing**: Multiple specialized models (U-2-Net, SILUETA, ISNet)
- **Edge Enhancement**: Advanced algorithms for hair and soft edge preservation
- **Manual Editing**: Brush and eraser tools for fine-tuning results
- **High Performance**: Redis caching, GPU acceleration support
- **Professional UI**: Modern, responsive interface with drag-and-drop
- **Multiple Formats**: Support for JPG, PNG up to 16MB
- **Download Ready**: High-quality PNG with transparent background

## 🚀 Quick Start

### Using Docker (Recommended)

1. **Clone the repository**
```bash
git clone <repository-url>
cd background-removal-tool
```

2. **Start the application**
```bash
docker-compose up -d
```

3. **Access the application**
- Frontend: http://localhost:8080
- Backend API: http://localhost:5000

### Manual Installation

#### Backend Setup

1. **Navigate to backend directory**
```bash
cd backend
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your settings
```

5. **Start the backend**
```bash
python app.py
```

#### Frontend Setup

1. **Navigate to frontend directory**
```bash
cd frontend
```

2. **Start a local server**
```bash
# Using Python
python -m http.server 8080

# Or using Node.js
npx serve -s . -p 8080
```

3. **Access the application**
Open http://localhost:8080 in your browser

## 📋 System Requirements

### Minimum Requirements
- **CPU**: 4 cores, 2.5 GHz
- **RAM**: 8 GB
- **Storage**: 10 GB free space
- **Python**: 3.8+

### Recommended for Production
- **CPU**: 8+ cores, 3.0+ GHz
- **RAM**: 16+ GB
- **GPU**: NVIDIA GPU with CUDA support (optional)
- **Storage**: SSD with 50+ GB free space

## 🔧 Configuration

### Backend Configuration (.env)

```env
# Basic Settings
FLASK_ENV=production
SECRET_KEY=your-secret-key

# Redis (optional but recommended)
REDIS_HOST=localhost
REDIS_PORT=6379

# File Limits
MAX_CONTENT_LENGTH=16777216  # 16MB

# Performance
WORKER_THREADS=4
MAX_CONCURRENT_PROCESSES=10
```

### Model Selection Guide

| Model | Best For | Speed | Quality |
|-------|----------|-------|---------|
| **General** | Most images | Fast | Good |
| **Human** | People, portraits | Fast | Excellent for humans |
| **Object** | Products, items | Medium | Great for objects |
| **Advanced** | Complex scenes | Slow | Highest quality |

## 🎯 API Endpoints

### Core Endpoints

```bash
# Health Check
GET /api/health

# Upload & Process
POST /api/upload
- Form data: image, model, enhance_edges

# Get Preview
GET /api/preview/{file_id}

# Download Result
GET /api/download/{file_id}

# Edit Mask
POST /api/edit-mask
- JSON: {file_id, edits[]}
```

### Example Usage

```javascript
// Upload image for processing
const formData = new FormData();
formData.append('image', imageFile);
formData.append('model', 'advanced');
formData.append('enhance_edges', 'true');

const response = await fetch('/api/upload', {
    method: 'POST',
    body: formData
});

const result = await response.json();
console.log('File ID:', result.file_id);
```

## 🎨 Frontend Integration

### Basic HTML Integration

```html
<input type="file" id="imageInput" accept="image/*">
<div id="result"></div>

<script>
document.getElementById('imageInput').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('image', file);
    formData.append('model', 'general');
    
    try {
        const response = await fetch('http://localhost:5000/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        if (data.success) {
            // Get preview
            const previewResponse = await fetch(`http://localhost:5000/api/preview/${data.file_id}`);
            const previewData = await previewResponse.json();
            
            document.getElementById('result').innerHTML = 
                `<img src="${previewData.preview}" alt="Result">`;
        }
    } catch (error) {
        console.error('Processing failed:', error);
    }
});
</script>
```

### React Integration

```jsx
import React, { useState } from 'react';

const BackgroundRemover = () => {
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);
    
    const processImage = async (file) => {
        setLoading(true);
        
        const formData = new FormData();
        formData.append('image', file);
        formData.append('model', 'advanced');
        
        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            if (data.success) {
                // Get preview
                const previewResponse = await fetch(`/api/preview/${data.file_id}`);
                const previewData = await previewResponse.json();
                setResult(previewData.preview);
            }
        } catch (error) {
            console.error('Error:', error);
        } finally {
            setLoading(false);
        }
    };
    
    return (
        <div>
            <input 
                type="file" 
                accept="image/*"
                onChange={(e) => processImage(e.target.files[0])}
            />
            {loading && <p>Processing...</p>}
            {result && <img src={result} alt="Result" />}
        </div>
    );
};
```

## 🚀 Production Deployment

### Docker Production

```bash
# Build production images
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# Deploy with production profile
docker-compose --profile production up -d
```

### AWS Deployment

1. **EC2 Instance Setup**
```bash
# Install Docker
sudo yum update -y
sudo yum install -y docker
sudo service docker start

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

2. **Environment Setup**
```bash
# Clone repository
git clone <your-repo>
cd background-removal-tool

# Configure production environment
cp backend/.env.example backend/.env
# Edit .env with production settings

# Deploy
docker-compose up -d
```

3. **Load Balancer Configuration**
- Use AWS Application Load Balancer
- Configure SSL certificate
- Set up auto-scaling group

### Performance Optimization

#### GPU Acceleration
```python
# Install CUDA support
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Verify GPU availability
python -c "import torch; print(torch.cuda.is_available())"
```

#### Redis Caching
```bash
# Install Redis
sudo apt-get install redis-server

# Configure Redis for production
sudo nano /etc/redis/redis.conf
# Set: maxmemory 2gb
# Set: maxmemory-policy allkeys-lru
```

## 📊 Performance Benchmarks

| Model | Average Time | Memory Usage | GPU Acceleration |
|-------|-------------|--------------|------------------|
| General | 2-4s | 1.5GB | 0.5-1s |
| Human | 2-3s | 1.8GB | 0.5-0.8s |
| Object | 3-5s | 2.0GB | 0.8-1.2s |
| Advanced | 5-8s | 2.5GB | 1.2-2s |

*Benchmarks on Intel i7-10700K, 32GB RAM, RTX 3080*

## 🔍 Edge Cases & Solutions

### Hair & Soft Edges
- Use `isnet-general-use` model
- Enable edge enhancement
- Apply Gaussian blur to mask edges
- Use alpha matting for complex areas

### Semi-Transparent Objects
- Preserve original alpha values
- Use composite blending modes
- Apply median filtering

### Complex Backgrounds
- Use ensemble of multiple models
- Pre-process with contrast enhancement
- Fallback to manual editing tools

## 🛠️ Troubleshooting

### Common Issues

**1. Out of Memory Errors**
```python
# Solution: Reduce image size before processing
def optimize_image(image, max_size=1024):
    if max(image.size) > max_size:
        ratio = max_size / max(image.size)
        new_size = tuple(int(dim * ratio) for dim in image.size)
        return image.resize(new_size, Image.Resampling.LANCZOS)
    return image
```

**2. Slow Processing**
- Enable Redis caching
- Use GPU acceleration
- Optimize image size
- Use faster models for real-time applications

**3. Poor Edge Quality**
- Enable edge enhancement
- Use advanced model
- Apply manual editing
- Adjust brush size for fine details

### Monitoring & Logging

```python
# Add performance monitoring
import time
import logging

def process_with_monitoring(image_path):
    start_time = time.time()
    
    try:
        result = process_background_removal(image_path)
        processing_time = time.time() - start_time
        
        logging.info(f"Processing completed in {processing_time:.2f}s")
        return result
        
    except Exception as e:
        logging.error(f"Processing failed: {str(e)}")
        raise
```

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review the API documentation

## 🔄 Updates & Roadmap

### Current Version: 1.0.0
- ✅ Basic background removal
- ✅ Multiple AI models
- ✅ Edge enhancement
- ✅ Manual editing tools
- ✅ Docker deployment

### Upcoming Features
- 🔲 Batch processing
- 🔲 Video background removal
- 🔲 Custom model training
- 🔲 Mobile app support
- 🔲 API rate limiting
- 🔲 User accounts & history

---

**Built with ❤️ for creators and developers**