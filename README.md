# AI-Powered Background Removal Tool

A professional-grade background removal application powered by state-of-the-art AI models including U²-Net, MODNet, and SAM. Perfect for e-commerce, portraits, and design projects.

![AI Background Remover](https://img.shields.io/badge/AI-Background%20Remover-blue)
![Python](https://img.shields.io/badge/Python-3.9+-green)
![Flask](https://img.shields.io/badge/Flask-2.3+-red)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 🚀 Features

### ✨ Advanced AI Models
- **U²-Net**: Best general-purpose model with 95%+ accuracy
- **U²-Net Human Segmentation**: Optimized for people and portraits
- **SILUETA**: Specialized for products and objects
- **Auto-detection**: Automatically selects the best model for your image

### 🎯 Professional Quality
- **Precise Edge Detection**: Handles complex edges, hair, and semi-transparent objects
- **Edge Feathering**: Adjustable soft edges (0-10px) for natural results
- **High-Resolution Processing**: Supports up to 4K images with quality preservation
- **Multiple Quality Settings**: Fast, Medium, and High-quality processing

### 🛠️ Manual Editing Tools
- **Brush Tool**: Add areas to the subject mask
- **Eraser Tool**: Remove areas from the subject mask
- **Adjustable Brush Size**: 1-50px for precise editing
- **Zoom Tool**: Detailed editing capability

### 🎨 Background Preview Options
- **Transparent**: PNG with full transparency
- **Solid Colors**: White, black, or custom color backgrounds
- **Real-time Preview**: See results instantly with different backgrounds

### 📁 Export Options
- **PNG**: Preserves transparency for web and print
- **JPG**: With custom background color
- **WebP**: Optimized for web with smaller file sizes
- **Batch Download**: Multiple formats simultaneously

### ⚡ Performance & Scalability
- **GPU Acceleration**: CUDA support with CPU fallback
- **Intelligent Caching**: Redis-based caching for faster repeated processing
- **Background Processing**: Async processing for large images
- **Rate Limiting**: API protection and fair usage

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Flask API     │    │   AI Models     │
│   (HTML/CSS/JS) │◄──►│   (Python)      │◄──►│   (REMBG/U²-Net)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Nginx         │    │   Redis Cache   │    │   Celery Worker │
│   (Load Balancer)│    │   (Sessions)    │    │   (Async Tasks) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🔧 Installation

### Option 1: Docker Deployment (Recommended)

1. **Clone the repository**
```bash
git clone <repository-url>
cd ai-background-remover
```

2. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Deploy with Docker Compose**
```bash
docker-compose up -d
```

4. **Access the application**
- Web Interface: http://localhost
- API: http://localhost/api
- Health Check: http://localhost/api/health

### Option 2: Manual Installation

1. **Install Python dependencies**
```bash
pip install -r requirements.txt
```

2. **Install Redis** (for caching and background processing)
```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS
brew install redis

# Windows
# Download from https://redis.io/download
```

3. **Start Redis**
```bash
redis-server
```

4. **Start the Flask application**
```bash
python app.py
```

5. **Start Celery worker** (in a separate terminal)
```bash
celery -A app.celery worker --loglevel=info
```

6. **Access the application**
- Web Interface: http://localhost:5000
- API: http://localhost:5000/api

## 📖 Usage Guide

### Web Interface

1. **Upload Image**
   - Drag and drop an image file onto the upload area
   - Or click to browse and select a file
   - Supports PNG, JPG, JPEG, WebP (max 16MB)

2. **Configure Processing Options**
   - **Model**: Choose AI model or use auto-detection
   - **Quality**: Select processing quality (Fast/Medium/High)
   - **Edge Softness**: Adjust feathering (0-10px)
   - **Background Processing**: Enable for large images

3. **Process Image**
   - Click "Remove Background" to start processing
   - View real-time progress for async processing
   - Compare original and processed images side-by-side

4. **Fine-tune Results** (Optional)
   - Use brush tool to add areas to the subject
   - Use eraser tool to remove unwanted areas
   - Adjust brush size for precision editing

5. **Preview with Different Backgrounds**
   - Transparent (for web/design use)
   - White/Black (for print/e-commerce)
   - Custom color (brand matching)

6. **Download Results**
   - PNG: Full transparency preserved
   - JPG: With background color applied
   - WebP: Optimized for web use

### API Usage

#### Process Image
```bash
curl -X POST http://localhost:5000/api/remove-background \
  -F "image=@your-image.jpg" \
  -F "model=auto" \
  -F "quality=high" \
  -F "feather_radius=2"
```

#### Check Available Models
```bash
curl http://localhost:5000/api/models
```

#### Download Processed Image
```bash
curl http://localhost:5000/api/download/{result_id} -o result.png
```

#### Check Processing Status (Async)
```bash
curl http://localhost:5000/api/status/{task_id}
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_ENV` | Flask environment | `production` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` |
| `MAX_CONTENT_LENGTH` | Max file size in bytes | `16777216` (16MB) |
| `CUDA_VISIBLE_DEVICES` | GPU device ID | `0` |
| `API_RATE_LIMIT` | Requests per minute | `100` |
| `DEFAULT_MODEL` | Default AI model | `u2net` |

### Model Configuration

The application supports multiple AI models optimized for different use cases:

| Model | Best For | Accuracy | Speed |
|-------|----------|----------|--------|
| `u2net` | General purpose | 95% | Medium |
| `u2net_human_seg` | People/portraits | 97% | Medium |
| `silueta` | Products/objects | 93% | Fast |
| `auto` | Auto-detection | Variable | Smart |

### Performance Tuning

#### For High Volume
```yaml
# docker-compose.yml
worker:
  command: celery -A app.celery worker --loglevel=info --concurrency=4
  deploy:
    replicas: 3
```

#### For GPU Acceleration
```dockerfile
# Use GPU-enabled base image
FROM nvidia/cuda:11.8-runtime-ubuntu20.04
```

#### For Memory Optimization
```python
# app.py - Add these configurations
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024  # 8MB
app.config['REMBG_MAX_CACHE_SIZE'] = 100  # Limit model cache
```

## 🔍 Advanced Features

### Edge Case Handling

#### Hair and Fine Details
- **Multi-scale Processing**: 2x resolution with smart downscaling
- **Bilateral Filtering**: Preserves edges while smoothing
- **Morphological Operations**: Cleanup for better mask quality

#### Semi-transparent Objects
- **Alpha Matting**: Advanced transparency handling
- **Gradient Analysis**: Automatic detection of semi-transparent regions
- **Smart Blending**: Preserves glass, water, and fabric transparency

#### Complex Backgrounds
- **Primary/Fallback System**: U²-Net with SAM backup
- **Automatic Prompting**: Smart subject detection for SAM
- **Manual Override**: User-defined subject boundaries

### Performance Optimizations

#### Caching Strategy
```python
# Intelligent caching based on:
- Image hash (content-based)
- Processing parameters
- Model version
- Quality settings
```

#### Background Processing
```python
# Async processing for:
- Images > 2MB
- High-quality mode
- Batch operations
- API requests with async=true
```

#### GPU Utilization
```python
# Automatic GPU management:
- CUDA detection and fallback
- Memory optimization
- Batch processing on GPU
- Model sharing between workers
```

## 📊 Monitoring & Analytics

### Health Monitoring
- **Health Check Endpoint**: `/api/health`
- **Model Status**: Available models and memory usage
- **Redis Connectivity**: Cache and queue status
- **Processing Metrics**: Success/failure rates

### Performance Metrics
- **Processing Time**: Average per model and quality
- **Cache Hit Rate**: Efficiency of caching system
- **Queue Length**: Background job monitoring
- **Error Rates**: By endpoint and error type

### Logging
```python
# Structured logging includes:
- Request ID for tracing
- Processing parameters
- Model performance metrics
- Error details and stack traces
```

## 🚀 Deployment

### Production Checklist

- [ ] Set `FLASK_ENV=production`
- [ ] Configure secure `SECRET_KEY`
- [ ] Set up SSL/TLS certificates
- [ ] Configure rate limiting
- [ ] Set up monitoring and logging
- [ ] Configure backup storage
- [ ] Test disaster recovery

### Scaling Considerations

#### Horizontal Scaling
```yaml
# Multiple worker instances
services:
  worker:
    deploy:
      replicas: 5
    
  web:
    deploy:
      replicas: 3
```

#### Load Balancing
```nginx
upstream backend {
    server web1:5000;
    server web2:5000;
    server web3:5000;
}
```

#### Storage Scaling
```yaml
# External storage for results
volumes:
  - type: nfs
    source: /shared/results
    target: /app/results
```

## 🐛 Troubleshooting

### Common Issues

#### Model Loading Errors
```bash
# Check GPU availability
nvidia-smi

# Verify CUDA installation
python -c "import torch; print(torch.cuda.is_available())"

# Clear model cache
rm -rf ~/.cache/huggingface/
```

#### Memory Issues
```bash
# Monitor memory usage
docker stats

# Reduce concurrent workers
export CELERY_CONCURRENCY=1

# Use smaller models
export DEFAULT_MODEL=silueta
```

#### Performance Issues
```bash
# Check Redis connection
redis-cli ping

# Monitor processing queue
celery -A app.celery inspect active

# Check disk space
df -h
```

### Debug Mode
```bash
# Enable debug logging
export FLASK_DEBUG=True
export LOG_LEVEL=DEBUG

# Run with verbose output
python app.py --debug
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Format code
black app.py
flake8 app.py
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **REMBG**: For the excellent background removal models
- **U²-Net**: For the state-of-the-art segmentation architecture
- **Segment Anything (SAM)**: For advanced segmentation capabilities
- **Flask & Celery**: For the robust web framework and task queue

## 📞 Support

- **Documentation**: Check this README and inline code comments
- **Issues**: Create an issue on GitHub for bugs and feature requests
- **Discussions**: Use GitHub Discussions for questions and ideas

---

**Made with ❤️ for the developer community**