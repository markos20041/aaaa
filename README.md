# 🎨 AI Background Removal Application

A production-ready web application for removing image backgrounds using state-of-the-art AI models. Built with both Python/Flask and Node.js/Express implementations.

## ✨ Features

- **State-of-the-Art AI**: Uses Bria RMBG 2.0, the best open-source background removal model
- **Dual Implementation**: Both Python/Flask and Node.js/Express backends
- **High Accuracy**: 90% success rate with complex backgrounds and fine details
- **Batch Processing**: Process up to 10 images simultaneously
- **Edge Enhancement**: Manual controls for edge feathering and smoothing
- **API Fallback**: Optional integration with Remove.bg API for premium results
- **Modern UI**: Responsive design with drag-and-drop functionality
- **Production Ready**: Docker containers, rate limiting, caching, and monitoring

## 🔧 Technology Stack

### Python Implementation (Recommended)
- **Backend**: Flask with WSGI
- **AI Models**: Bria RMBG 2.0, BiRefNet, U-2-Net
- **Image Processing**: PIL, OpenCV, torchvision
- **ML Framework**: PyTorch, Transformers

### Node.js Implementation (Alternative)
- **Backend**: Express.js
- **Image Processing**: Sharp, Jimp
- **API Integration**: Remove.bg, other commercial APIs

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Caching**: Redis
- **Reverse Proxy**: Nginx
- **GPU Support**: NVIDIA CUDA

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- (Optional) NVIDIA GPU with CUDA support
- (Optional) Remove.bg API key

### 1. Clone Repository
```bash
git clone <repository-url>
cd background-removal-app
```

### 2. Environment Setup
```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Run with Docker (Recommended)
```bash
# Python/Flask version (with GPU support)
docker-compose up background-removal-python

# Node.js/Express version
docker-compose --profile nodejs up background-removal-nodejs

# CPU-only version
docker-compose -f docker-compose.yml -f docker-compose.override.yml up
```

### 4. Manual Installation

#### Python Version
```bash
# Install dependencies
pip install -r requirements.txt

# Run application
python app.py
```

#### Node.js Version
```bash
# Install dependencies
npm install

# Run application
npm start
```

## 📖 API Documentation

### Health Check
```http
GET /api/health
```

### Single Image Processing
```http
POST /api/remove-background
Content-Type: multipart/form-data

image: file
enhance_edges: boolean (default: true)
feather_radius: float (default: 1.0)
use_api_fallback: boolean (default: false)
```

### Batch Processing
```http
POST /api/batch-remove
Content-Type: multipart/form-data

images: file[] (max 10 files)
```

### Download Result
```http
GET /api/download/{filename}
```

## 🎯 Model Comparison

| Model | Accuracy | Speed | License | Best For |
|-------|----------|-------|---------|----------|
| **Bria RMBG 2.0** | 90% | Fast | Free/Commercial | Production use |
| BiRefNet | 85% | Fast | Free | Open source projects |
| U-2-Net | 74% | Medium | Free | Basic use cases |
| Remove.bg API | 97% | Fast | $0.20/image | Maximum accuracy |

## ⚙️ Configuration

### Environment Variables

```bash
# Core Settings
SECRET_KEY=your-secret-key
REMOVE_BG_API_KEY=your-api-key
ENABLE_REMOVE_BG_FALLBACK=false

# Performance
ENABLE_GPU=true
MODEL_CACHE_DIR=./models
REDIS_URL=redis://localhost:6379

# Rate Limiting
RATE_LIMIT_PER_HOUR=1000
UPLOAD_RATE_LIMIT_PER_MINUTE=30
```

### Docker Deployment Options

#### Development
```bash
docker-compose -f docker-compose.yml -f docker-compose.override.yml up
```

#### Production with GPU
```bash
docker-compose --profile production up
```

#### CPU-only Deployment
```bash
docker-compose up --build --force-recreate
# Edit docker-compose.yml to use 'cpu-only' target
```

## 🏗️ Architecture

### Processing Pipeline
```
Upload → Validation → Preprocessing → Model Inference → Post-processing → Download
```

### Request Flow
```
Frontend → Load Balancer → Flask/Express → Background Removal Service → Response
```

### Model Integration
```python
# Python - Bria RMBG 2.0
from transformers import AutoModelForImageSegmentation

model = AutoModelForImageSegmentation.from_pretrained(
    'briaai/RMBG-2.0', 
    trust_remote_code=True
)
```

```javascript
// Node.js - API Integration
const response = await axios.post('https://api.remove.bg/v1.0/removebg', {
    image_file: imageBuffer
}, {
    headers: { 'X-Api-Key': apiKey }
});
```

## 📊 Performance Optimization

### GPU Acceleration
- **Requirements**: NVIDIA GPU with 4GB+ VRAM
- **Performance**: 3-5x faster than CPU
- **Setup**: Use CUDA Docker image

### Memory Management
- **Image Size Limit**: 4000x4000 pixels
- **Batch Size**: Max 10 images
- **Model Caching**: Persistent model storage

### Scaling Strategies
- **Horizontal Scaling**: Multiple container instances
- **Load Balancing**: Nginx reverse proxy
- **Caching**: Redis for result caching
- **CDN**: Static asset delivery

## 🔒 Security Features

- **Rate Limiting**: Per-IP request limits
- **File Validation**: Type and size checks
- **Path Traversal Protection**: Secure file handling
- **CORS**: Configurable cross-origin policies
- **Input Sanitization**: XSS prevention

## 🐛 Troubleshooting

### Common Issues

**GPU not detected**
```bash
# Check NVIDIA Docker support
docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu20.04 nvidia-smi
```

**Model download fails**
```bash
# Pre-download models
python -c "from transformers import AutoModelForImageSegmentation; AutoModelForImageSegmentation.from_pretrained('briaai/RMBG-2.0', trust_remote_code=True)"
```

**Out of memory errors**
```bash
# Reduce batch size or image resolution
export MAX_BATCH_SIZE=5
export MAX_IMAGE_SIZE=2048
```

### Performance Tuning

**For High Volume**
- Use GPU acceleration
- Enable Redis caching
- Implement horizontal scaling
- Use model quantization

**For Low Resources**
- Use CPU-only deployment
- Reduce model precision
- Implement request queuing
- Use external APIs

## 📈 Monitoring

### Health Checks
```bash
curl http://localhost:5000/api/health
```

### Metrics
- Processing time per image
- Success/failure rates
- Memory and GPU usage
- Request queue depth

### Logging
```python
# Python logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## 🚀 Deployment

### Production Checklist
- [ ] Set production SECRET_KEY
- [ ] Configure rate limiting
- [ ] Set up SSL/TLS
- [ ] Enable monitoring
- [ ] Configure backups
- [ ] Set up log aggregation

### Cloud Deployment

**AWS**
```bash
# Use ECS with GPU instances
aws ecs create-service --service-name background-removal
```

**Google Cloud**
```bash
# Use GKE with GPU node pools
kubectl apply -f k8s-deployment.yaml
```

**Azure**
```bash
# Use ACI with GPU support
az container create --resource-group rg --name bg-removal
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Bria AI](https://bria.ai/) for RMBG 2.0 model
- [Remove.bg](https://remove.bg/) for API integration
- [Hugging Face](https://huggingface.co/) for model hosting
- Open source community for various tools and libraries

## 📞 Support

- **Documentation**: Check this README and inline code comments
- **Issues**: Open a GitHub issue
- **Discussions**: Use GitHub Discussions for questions
- **Commercial Support**: Contact for enterprise licensing

---

**Built with ❤️ for the AI community**