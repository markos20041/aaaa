/**
 * AI-Powered Background Removal API - Node.js/Express Implementation
 * Alternative to the FastAPI version with similar functionality
 */

const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs').promises;
const { spawn } = require('child_process');
const sharp = require('sharp');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const { v4: uuidv4 } = require('uuid');

// Configuration
const config = {
    port: process.env.PORT || 8000,
    maxFileSize: 50 * 1024 * 1024, // 50MB
    allowedExtensions: ['.jpg', '.jpeg', '.png', '.webp'],
    tempDir: './temp',
    modelsDir: './models',
    staticDir: './static',
    templatesDir: './templates',
    maxBatchSize: 10,
    device: process.env.DEVICE || 'auto'
};

// Create Express app
const app = express();

// Middleware
app.use(helmet());
app.use(cors());
app.use(express.json());
app.use(express.static(config.staticDir));

// Rate limiting
const limiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 100, // limit each IP to 100 requests per windowMs
    message: 'Too many requests from this IP, please try again later.'
});
app.use('/remove-background', limiter);

// Configure multer for file uploads
const storage = multer.diskStorage({
    destination: async (req, file, cb) => {
        try {
            await fs.mkdir(config.tempDir, { recursive: true });
            cb(null, config.tempDir);
        } catch (error) {
            cb(error);
        }
    },
    filename: (req, file, cb) => {
        const uniqueName = `${uuidv4()}${path.extname(file.originalname)}`;
        cb(null, uniqueName);
    }
});

const upload = multer({
    storage: storage,
    limits: {
        fileSize: config.maxFileSize,
        files: config.maxBatchSize
    },
    fileFilter: (req, file, cb) => {
        const ext = path.extname(file.originalname).toLowerCase();
        if (config.allowedExtensions.includes(ext)) {
            cb(null, true);
        } else {
            cb(new Error(`Unsupported file type: ${ext}`));
        }
    }
});

// Utility functions
class ImageProcessor {
    constructor() {
        this.pythonProcess = null;
        this.isReady = false;
    }

    async initialize() {
        try {
            // Check if Python dependencies are available
            await this.checkPythonDependencies();
            this.isReady = true;
            console.log('✅ Image processor initialized successfully');
        } catch (error) {
            console.error('❌ Failed to initialize image processor:', error.message);
            throw error;
        }
    }

    async checkPythonDependencies() {
        return new Promise((resolve, reject) => {
            const pythonCheck = spawn('python3', ['-c', 'import rembg, PIL; print("Dependencies OK")']);
            
            pythonCheck.on('close', (code) => {
                if (code === 0) {
                    resolve();
                } else {
                    reject(new Error('Python dependencies not found. Please install: pip install rembg pillow'));
                }
            });

            pythonCheck.on('error', (error) => {
                reject(new Error(`Python not found: ${error.message}`));
            });
        });
    }

    async removeBackground(inputPath, options = {}) {
        const outputPath = inputPath.replace(path.extname(inputPath), '_output.png');
        
        try {
            // Create Python script for background removal
            const pythonScript = this.createPythonScript(options);
            const tempScriptPath = path.join(config.tempDir, `script_${uuidv4()}.py`);
            
            await fs.writeFile(tempScriptPath, pythonScript);

            // Execute Python script
            const result = await this.executePythonScript(tempScriptPath, inputPath, outputPath);
            
            // Clean up script
            await fs.unlink(tempScriptPath);

            return {
                outputPath,
                ...result
            };
        } catch (error) {
            throw new Error(`Background removal failed: ${error.message}`);
        }
    }

    createPythonScript(options) {
        const {
            model_type = 'u2net',
            enhance_edges = true,
            feather_amount = 2,
            alpha_matting = false
        } = options;

        return `
import sys
import time
import json
from PIL import Image, ImageFilter
import numpy as np
from rembg import remove, new_session
import cv2

def enhance_edges(mask, amount=2):
    if amount == 0:
        return mask
    
    mask_np = np.array(mask)
    kernel = np.ones((amount, amount), np.uint8)
    mask_np = cv2.morphologyEx(mask_np, cv2.MORPH_CLOSE, kernel)
    mask_np = cv2.morphologyEx(mask_np, cv2.MORPH_OPEN, kernel)
    return Image.fromarray(mask_np)

def apply_feathering(mask, feather_amount=2):
    if feather_amount == 0:
        return mask
    return mask.filter(ImageFilter.GaussianBlur(radius=feather_amount))

def main():
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    
    start_time = time.time()
    
    try:
        # Load image
        with Image.open(input_path) as img:
            original_size = img.size
            
            # Remove background
            session = new_session('${model_type}')
            
            # Convert to bytes for rembg
            import io
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            
            # Remove background
            result_bytes = remove(img_byte_arr, session=session)
            result_img = Image.open(io.BytesIO(result_bytes))
            
            # Post-processing
            if result_img.mode == 'RGBA':
                alpha = result_img.split()[-1]
                
                # Enhance edges
                if ${enhance_edges}:
                    alpha = enhance_edges(alpha, 2)
                
                # Apply feathering
                if ${feather_amount} > 0:
                    alpha = apply_feathering(alpha, ${feather_amount})
                
                # Reapply processed alpha
                rgb = result_img.convert('RGB')
                result_img = rgb.copy()
                result_img.putalpha(alpha)
            
            # Save result
            result_img.save(output_path, 'PNG', optimize=True)
            
            processing_time = time.time() - start_time
            
            # Return metadata
            metadata = {
                "processing_time": processing_time,
                "model_used": "${model_type}",
                "image_size": original_size,
                "success": True
            }
            
            print(json.dumps(metadata))
            
    except Exception as e:
        error_metadata = {
            "success": False,
            "error": str(e),
            "processing_time": time.time() - start_time
        }
        print(json.dumps(error_metadata))
        sys.exit(1)

if __name__ == "__main__":
    main()
`;
    }

    async executePythonScript(scriptPath, inputPath, outputPath) {
        return new Promise((resolve, reject) => {
            const pythonProcess = spawn('python3', [scriptPath, inputPath, outputPath]);
            
            let stdout = '';
            let stderr = '';

            pythonProcess.stdout.on('data', (data) => {
                stdout += data.toString();
            });

            pythonProcess.stderr.on('data', (data) => {
                stderr += data.toString();
            });

            pythonProcess.on('close', (code) => {
                if (code === 0) {
                    try {
                        const result = JSON.parse(stdout.trim());
                        resolve(result);
                    } catch (parseError) {
                        reject(new Error(`Failed to parse result: ${parseError.message}`));
                    }
                } else {
                    reject(new Error(`Python script failed: ${stderr}`));
                }
            });

            pythonProcess.on('error', (error) => {
                reject(new Error(`Failed to execute Python script: ${error.message}`));
            });
        });
    }

    async getImageInfo(imagePath) {
        try {
            const metadata = await sharp(imagePath).metadata();
            const stats = await fs.stat(imagePath);
            
            return {
                width: metadata.width,
                height: metadata.height,
                format: metadata.format,
                size: stats.size,
                channels: metadata.channels
            };
        } catch (error) {
            throw new Error(`Failed to get image info: ${error.message}`);
        }
    }

    async cleanup(filePath) {
        try {
            await fs.unlink(filePath);
        } catch (error) {
            console.warn(`Failed to cleanup file ${filePath}:`, error.message);
        }
    }
}

// Initialize image processor
const imageProcessor = new ImageProcessor();

// Error handling middleware
const handleError = (error, req, res, next) => {
    console.error('Error:', error);
    
    if (error instanceof multer.MulterError) {
        if (error.code === 'LIMIT_FILE_SIZE') {
            return res.status(413).json({
                error: 'File too large',
                maxSize: `${config.maxFileSize / (1024 * 1024)}MB`
            });
        }
        if (error.code === 'LIMIT_FILE_COUNT') {
            return res.status(400).json({
                error: 'Too many files',
                maxFiles: config.maxBatchSize
            });
        }
    }
    
    if (error.message.includes('Unsupported file type')) {
        return res.status(400).json({
            error: error.message,
            allowedTypes: config.allowedExtensions
        });
    }
    
    res.status(500).json({
        error: 'Internal server error',
        message: process.env.NODE_ENV === 'development' ? error.message : 'Something went wrong'
    });
};

// Routes
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, '../templates/index.html'));
});

app.get('/health', (req, res) => {
    const memUsage = process.memoryUsage();
    
    res.json({
        status: imageProcessor.isReady ? 'healthy' : 'initializing',
        uptime: process.uptime(),
        memory: {
            used: Math.round(memUsage.heapUsed / 1024 / 1024), // MB
            total: Math.round(memUsage.heapTotal / 1024 / 1024) // MB
        },
        device: config.device,
        nodeVersion: process.version,
        platform: process.platform
    });
});

app.post('/remove-background', upload.single('file'), async (req, res) => {
    if (!imageProcessor.isReady) {
        return res.status(503).json({
            error: 'Service not ready',
            message: 'Image processor is still initializing'
        });
    }

    if (!req.file) {
        return res.status(400).json({
            error: 'No file uploaded',
            message: 'Please provide an image file'
        });
    }

    const startTime = Date.now();
    const inputPath = req.file.path;
    let outputPath = null;

    try {
        // Get processing options
        const options = {
            model_type: req.body.model_type || 'u2net',
            enhance_edges: req.body.enhance_edges === 'true',
            feather_amount: parseInt(req.body.feather_amount) || 2,
            alpha_matting: req.body.alpha_matting === 'true'
        };

        // Get image info
        const imageInfo = await imageProcessor.getImageInfo(inputPath);

        // Process image
        const result = await imageProcessor.removeBackground(inputPath, options);
        outputPath = result.outputPath;

        // Read processed image
        const processedImage = await fs.readFile(outputPath);

        // Set response headers
        const totalTime = (Date.now() - startTime) / 1000;
        res.set({
            'Content-Type': 'image/png',
            'Content-Disposition': `attachment; filename="bg_removed_${req.file.originalname.replace(/\.[^/.]+$/, '')}.png"`,
            'X-Processing-Time': totalTime.toFixed(2),
            'X-Model-Used': result.model_used || options.model_type,
            'X-Image-Size': `${imageInfo.width}x${imageInfo.height}`,
            'X-Original-Size': imageInfo.size
        });

        res.send(processedImage);

    } catch (error) {
        console.error('Processing error:', error);
        res.status(500).json({
            error: 'Processing failed',
            message: error.message
        });
    } finally {
        // Cleanup
        if (inputPath) {
            await imageProcessor.cleanup(inputPath);
        }
        if (outputPath) {
            await imageProcessor.cleanup(outputPath);
        }
    }
});

app.post('/batch-remove-background', upload.array('files', config.maxBatchSize), async (req, res) => {
    if (!imageProcessor.isReady) {
        return res.status(503).json({
            error: 'Service not ready',
            message: 'Image processor is still initializing'
        });
    }

    if (!req.files || req.files.length === 0) {
        return res.status(400).json({
            error: 'No files uploaded',
            message: 'Please provide image files'
        });
    }

    const results = [];
    const options = {
        model_type: req.body.model_type || 'u2net',
        enhance_edges: req.body.enhance_edges === 'true',
        feather_amount: parseInt(req.body.feather_amount) || 2,
        alpha_matting: req.body.alpha_matting === 'true'
    };

    // Process each file
    for (const file of req.files) {
        const startTime = Date.now();
        let outputPath = null;

        try {
            const result = await imageProcessor.removeBackground(file.path, options);
            outputPath = result.outputPath;

            results.push({
                filename: file.originalname,
                success: true,
                processing_time: (Date.now() - startTime) / 1000,
                model_used: result.model_used || options.model_type,
                size: `${result.width || 'unknown'}x${result.height || 'unknown'}`
            });

        } catch (error) {
            console.error(`Error processing ${file.originalname}:`, error);
            results.push({
                filename: file.originalname,
                success: false,
                error: error.message,
                processing_time: (Date.now() - startTime) / 1000
            });
        } finally {
            // Cleanup
            await imageProcessor.cleanup(file.path);
            if (outputPath) {
                await imageProcessor.cleanup(outputPath);
            }
        }
    }

    res.json({ results });
});

app.get('/models', (req, res) => {
    res.json({
        available_models: {
            'u2net': {
                name: 'U2-Net',
                description: 'Good general purpose background removal',
                loaded: true
            },
            'u2net_human_seg': {
                name: 'U2-Net Human Segmentation',
                description: 'Optimized for human subjects',
                loaded: true
            },
            'silueta': {
                name: 'Silueta',
                description: 'Fast processing for simple images',
                loaded: true
            }
        },
        recommended: 'u2net'
    });
});

// Error handling
app.use(handleError);

// 404 handler
app.use((req, res) => {
    res.status(404).json({
        error: 'Not found',
        message: 'The requested endpoint does not exist'
    });
});

// Start server
async function startServer() {
    try {
        // Initialize image processor
        await imageProcessor.initialize();

        // Ensure directories exist
        await fs.mkdir(config.tempDir, { recursive: true });
        await fs.mkdir(config.modelsDir, { recursive: true });

        // Start listening
        app.listen(config.port, () => {
            console.log(`
🎨 AI Background Removal API (Node.js/Express)
🚀 Server running on http://localhost:${config.port}
📚 Health check: http://localhost:${config.port}/health
🌐 Web interface: http://localhost:${config.port}
            `);
        });

    } catch (error) {
        console.error('❌ Failed to start server:', error.message);
        process.exit(1);
    }
}

// Graceful shutdown
process.on('SIGTERM', () => {
    console.log('🛑 Received SIGTERM, shutting down gracefully...');
    process.exit(0);
});

process.on('SIGINT', () => {
    console.log('🛑 Received SIGINT, shutting down gracefully...');
    process.exit(0);
});

// Start the server
startServer();

module.exports = app;