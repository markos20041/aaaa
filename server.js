const express = require('express');
const multer = require('multer');
const sharp = require('sharp');
const axios = require('axios');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const path = require('path');
const fs = require('fs').promises;
const { v4: uuidv4 } = require('uuid');
const compression = require('compression');
const morgan = require('morgan');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(helmet());
app.use(compression());
app.use(morgan('combined'));
app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // limit each IP to 100 requests per windowMs
  message: 'Too many requests from this IP, please try again later.',
});

const uploadLimiter = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: 30, // limit each IP to 30 uploads per minute
  message: 'Too many uploads, please try again later.',
});

app.use(limiter);

// Ensure directories exist
const ensureDirExists = async (dir) => {
  try {
    await fs.access(dir);
  } catch {
    await fs.mkdir(dir, { recursive: true });
  }
};

// Initialize directories
(async () => {
  await ensureDirExists('./uploads');
  await ensureDirExists('./outputs');
  await ensureDirExists('./public');
})();

// Multer configuration for file uploads
const storage = multer.memoryStorage();
const upload = multer({
  storage,
  limits: {
    fileSize: 50 * 1024 * 1024, // 50MB limit
  },
  fileFilter: (req, file, cb) => {
    const allowedMimes = ['image/jpeg', 'image/png', 'image/webp'];
    if (allowedMimes.includes(file.mimetype)) {
      cb(null, true);
    } else {
      cb(new Error('Invalid file type. Only JPEG, PNG, and WebP are allowed.'));
    }
  },
});

// Serve static files
app.use('/static', express.static('public'));
app.use('/outputs', express.static('outputs'));

class BackgroundRemovalService {
  constructor() {
    this.removeApiKey = process.env.REMOVE_BG_API_KEY;
    this.enableRemoveBgFallback = process.env.ENABLE_REMOVE_BG_FALLBACK === 'true';
  }

  async removeBackgroundRemoveBg(imageBuffer) {
    if (!this.removeApiKey) {
      throw new Error('Remove.bg API key not configured');
    }

    const formData = new FormData();
    const blob = new Blob([imageBuffer], { type: 'image/png' });
    formData.append('image_file', blob);
    formData.append('size', 'auto');

    const response = await axios.post('https://api.remove.bg/v1.0/removebg', formData, {
      headers: {
        'X-Api-Key': this.removeApiKey,
        'Content-Type': 'multipart/form-data',
      },
      responseType: 'arraybuffer',
      timeout: 30000,
    });

    if (response.status !== 200) {
      throw new Error(`Remove.bg API error: ${response.status}`);
    }

    return Buffer.from(response.data);
  }

  async removeBackgroundLocal(imageBuffer) {
    // For the Node.js version, we'll use a simple edge detection + masking approach
    // This is a basic implementation - in production, you'd integrate with a proper ML model
    
    try {
      // Convert to Sharp object
      const image = sharp(imageBuffer);
      const { width, height } = await image.metadata();

      // Basic processing: create a simple mask based on edge detection
      // This is a placeholder - replace with actual ML model integration
      const processedImage = await image
        .resize(Math.min(width, 1024), Math.min(height, 1024), {
          fit: 'inside',
          withoutEnlargement: true,
        })
        .png()
        .toBuffer();

      // For demo purposes, we'll return the image with a simple alpha channel
      // In a real implementation, you'd use an ML model like RMBG or U-2-Net
      const result = await sharp(processedImage)
        .composite([{
          input: Buffer.from([255, 255, 255, 128]), // Semi-transparent overlay for demo
          raw: { width: 1, height: 1, channels: 4 },
          tile: true,
          blend: 'multiply'
        }])
        .png()
        .toBuffer();

      return result;
    } catch (error) {
      throw new Error(`Local processing failed: ${error.message}`);
    }
  }

  async enhanceEdges(imageBuffer, featherRadius = 1.0) {
    if (featherRadius <= 0) return imageBuffer;

    try {
      return await sharp(imageBuffer)
        .blur(featherRadius * 0.5)
        .png()
        .toBuffer();
    } catch (error) {
      console.error('Edge enhancement failed:', error);
      return imageBuffer;
    }
  }

  async processImage(imageBuffer, options = {}) {
    const {
      useApiFallback = false,
      enhanceEdges = true,
      featherRadius = 1.0
    } = options;

    let result;
    let method;
    let confidence = 0.8; // Default confidence

    try {
      if (useApiFallback && this.enableRemoveBgFallback && this.removeApiKey) {
        result = await this.removeBackgroundRemoveBg(imageBuffer);
        method = 'Remove.bg API';
        confidence = 0.95;
      } else {
        result = await this.removeBackgroundLocal(imageBuffer);
        method = 'Local Processing (Demo)';
        confidence = 0.75;
      }

      // Enhance edges if requested
      if (enhanceEdges && featherRadius > 0) {
        result = await this.enhanceEdges(result, featherRadius);
      }

      return {
        image: result,
        confidence,
        method,
        success: true
      };

    } catch (error) {
      console.error('Background removal failed:', error);
      return {
        error: error.message,
        success: false
      };
    }
  }
}

const bgService = new BackgroundRemovalService();

// Routes

// Health check
app.get('/api/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'Node.js Background Removal Service',
    timestamp: new Date().toISOString(),
    enableRemoveBgFallback: bgService.enableRemoveBgFallback
  });
});

// Main background removal endpoint
app.post('/api/remove-background', uploadLimiter, upload.single('image'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No image file provided' });
    }

    const { buffer, originalname, mimetype } = req.file;
    
    // Get processing options
    const enhanceEdges = req.body.enhance_edges !== 'false';
    const featherRadius = parseFloat(req.body.feather_radius) || 1.0;
    const useApiFallback = req.body.use_api_fallback === 'true';

    // Validate image size
    const metadata = await sharp(buffer).metadata();
    if (metadata.width * metadata.height > 4000 * 4000) {
      return res.status(400).json({ error: 'Image too large. Maximum 4000x4000 pixels' });
    }

    // Process image
    const startTime = Date.now();
    const result = await bgService.processImage(buffer, {
      useApiFallback,
      enhanceEdges,
      featherRadius
    });

    if (!result.success) {
      return res.status(500).json({ error: result.error });
    }

    // Save result
    const filename = originalname || 'image.png';
    const nameWithoutExt = path.parse(filename).name;
    const outputFilename = `${nameWithoutExt}_no_bg_${Date.now()}.png`;
    const outputPath = path.join('./outputs', outputFilename);

    await fs.writeFile(outputPath, result.image);

    const processingTime = (Date.now() - startTime) / 1000;

    res.json({
      success: true,
      confidence: result.confidence,
      method: result.method,
      filename: outputFilename,
      download_url: `/api/download/${outputFilename}`,
      processing_time: `${processingTime.toFixed(1)}s`
    });

  } catch (error) {
    console.error('Processing error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Batch processing endpoint
app.post('/api/batch-remove', uploadLimiter, upload.array('images', 10), async (req, res) => {
  try {
    if (!req.files || req.files.length === 0) {
      return res.status(400).json({ error: 'No images provided' });
    }

    if (req.files.length > 10) {
      return res.status(400).json({ error: 'Maximum 10 images per batch' });
    }

    const results = [];

    for (let i = 0; i < req.files.length; i++) {
      const file = req.files[i];
      
      try {
        // Process each image
        const result = await bgService.processImage(file.buffer);

        if (result.success) {
          // Save result
          const filename = file.originalname || `image_${i}.png`;
          const nameWithoutExt = path.parse(filename).name;
          const outputFilename = `${nameWithoutExt}_no_bg_${Date.now()}_${i}.png`;
          const outputPath = path.join('./outputs', outputFilename);

          await fs.writeFile(outputPath, result.image);

          results.push({
            index: i,
            filename: file.originalname,
            success: true,
            confidence: result.confidence,
            method: result.method,
            output_filename: outputFilename,
            download_url: `/api/download/${outputFilename}`
          });
        } else {
          results.push({
            index: i,
            filename: file.originalname,
            success: false,
            error: result.error
          });
        }
      } catch (error) {
        results.push({
          index: i,
          filename: file.originalname,
          success: false,
          error: error.message
        });
      }
    }

    res.json({
      success: true,
      results,
      total_processed: results.filter(r => r.success).length,
      total_failed: results.filter(r => !r.success).length
    });

  } catch (error) {
    console.error('Batch processing error:', error);
    res.status(500).json({ error: 'Batch processing failed' });
  }
});

// Download endpoint
app.get('/api/download/:filename', async (req, res) => {
  try {
    const filename = req.params.filename;
    
    // Security: ensure filename doesn't contain path traversal
    if (filename.includes('..') || filename.includes('/') || filename.includes('\\')) {
      return res.status(400).json({ error: 'Invalid filename' });
    }

    const filePath = path.join('./outputs', filename);
    
    try {
      await fs.access(filePath);
      res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
      res.setHeader('Content-Type', 'image/png');
      res.sendFile(path.resolve(filePath));
    } catch {
      res.status(404).json({ error: 'File not found' });
    }
  } catch (error) {
    console.error('Download error:', error);
    res.status(500).json({ error: 'Download failed' });
  }
});

// Serve the main application page
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'templates', 'index.html'));
});

// Error handling middleware
app.use((error, req, res, next) => {
  if (error instanceof multer.MulterError) {
    if (error.code === 'LIMIT_FILE_SIZE') {
      return res.status(413).json({ error: 'File too large. Maximum 50MB allowed' });
    }
    return res.status(400).json({ error: error.message });
  }
  
  console.error('Unhandled error:', error);
  res.status(500).json({ error: 'Internal server error' });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({ error: 'Endpoint not found' });
});

// Cleanup old files periodically (every hour)
setInterval(async () => {
  try {
    const outputDir = './outputs';
    const files = await fs.readdir(outputDir);
    const now = Date.now();
    const maxAge = 24 * 60 * 60 * 1000; // 24 hours

    for (const file of files) {
      const filePath = path.join(outputDir, file);
      const stats = await fs.stat(filePath);
      
      if (now - stats.mtime.getTime() > maxAge) {
        await fs.unlink(filePath);
        console.log(`Cleaned up old file: ${file}`);
      }
    }
  } catch (error) {
    console.error('Cleanup error:', error);
  }
}, 60 * 60 * 1000); // Run every hour

// Start server
app.listen(PORT, () => {
  console.log(`Background Removal Server running on port ${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/api/health`);
  console.log(`Application: http://localhost:${PORT}`);
  
  if (bgService.enableRemoveBgFallback) {
    console.log('Remove.bg API fallback enabled');
  } else {
    console.log('Using local processing only');
  }
});

module.exports = app;