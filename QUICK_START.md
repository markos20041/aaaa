# 🚀 Quick Start Guide - AI Background Remover

Get your AI-powered background removal tool running in under 5 minutes!

## ⚡ Super Quick Start (Docker)

```bash
# 1. Run the automated setup
./setup.sh

# 2. Choose option 1 (Docker Compose) when prompted

# 3. Access your app
# Web: http://localhost
# API: http://localhost/api
```

That's it! 🎉

## 🛠️ Manual Installation (5 minutes)

### Prerequisites
- Python 3.9+
- Redis (will be installed automatically)

### Steps

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up environment
cp .env.example .env

# 3. Start Redis (automatic in setup script)
redis-server --daemonize yes

# 4. Start the Flask app
python app.py

# 5. Start Celery worker (new terminal)
celery -A app.celery worker --loglevel=info
```

Access at: http://localhost:5000

## 🧪 Test Your Installation

1. **Visit the web interface**
2. **Upload a test image** (drag & drop or click)
3. **Click "Remove Background"**
4. **Download the result**

## 📊 Recommended Test Images

- **Portrait**: Person with clear background
- **Product**: Object on solid background  
- **Complex**: Person with hair details
- **E-commerce**: Product with reflection

## 🎯 Common Use Cases

### E-commerce Product Photos
```
Original → AI Processing → White Background → Professional Product Image
```

### Profile Pictures
```
Casual Photo → AI Processing → Transparent → Professional Headshot
```

### Design Assets
```
Stock Photo → AI Processing → Transparent → Design Element
```

## ⚙️ Quick Configuration

### High-Quality Processing
```env
# .env
DEFAULT_MODEL=u2net
QUALITY=high
```

### Performance Optimization
```env
# .env
CELERY_CONCURRENCY=4
CACHE_CLEANUP_HOURS=1
```

### GPU Acceleration
```env
# .env
CUDA_VISIBLE_DEVICES=0
```

## 🔧 API Quick Reference

### Process Image
```bash
curl -X POST http://localhost:5000/api/remove-background \
  -F "image=@photo.jpg" \
  -F "model=auto" \
  -F "quality=high"
```

### Check Status
```bash
curl http://localhost:5000/api/status/{task_id}
```

### Download Result
```bash
curl http://localhost:5000/api/download/{result_id} -o result.png
```

## 🐛 Quick Troubleshooting

### Port Already in Use
```bash
# Kill process on port 5000
lsof -ti:5000 | xargs kill -9

# Or use different port
export FLASK_RUN_PORT=5001
```

### Model Loading Issues
```bash
# Clear cache
rm -rf ~/.cache/huggingface/

# Restart application
```

### Memory Issues
```bash
# Reduce image size limit
export MAX_CONTENT_LENGTH=8388608  # 8MB
```

### Redis Connection Issues
```bash
# Check Redis status
redis-cli ping

# Start Redis
redis-server --daemonize yes
```

## 🚀 Performance Tips

1. **Use GPU** if available (3-5x faster)
2. **Enable caching** for repeated images
3. **Use async processing** for large images
4. **Choose appropriate model** for your use case

## 📈 Scaling for Production

### Docker Compose (Recommended)
- ✅ Load balancing with Nginx
- ✅ Auto-scaling workers  
- ✅ Redis clustering
- ✅ Health monitoring

### Manual Scaling
```bash
# Multiple workers
celery -A app.celery worker --concurrency=8

# Multiple Flask instances
gunicorn --workers=4 --bind=0.0.0.0:5000 app:app
```

## 🔒 Security Checklist

- [ ] Change default secret key
- [ ] Set up rate limiting
- [ ] Configure CORS properly
- [ ] Use HTTPS in production
- [ ] Set up firewall rules

## 📞 Need Help?

- **Documentation**: Full README.md
- **Issues**: GitHub Issues
- **API Docs**: Built-in at `/api/docs`
- **Health Check**: `/api/health`

## 🎉 Success Metrics

You'll know it's working when:
- ✅ Health check returns "healthy"
- ✅ Upload shows image preview
- ✅ Processing completes without errors
- ✅ Download produces clean PNG

---

**Happy background removing! 🖼️✨**

*Pro tip: Start with the auto-detect model and high quality for best results.*