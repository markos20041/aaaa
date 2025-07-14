"""
AI-Powered Background Removal API
Production-ready FastAPI implementation with RMBG 2.0 and advanced features
"""

import os
import io
import time
import asyncio
from typing import Optional, List
import uuid
from pathlib import Path

import torch
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance
import cv2
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
from pydantic import BaseModel, Field
from transformers import AutoModelForImageSegmentation
from torchvision import transforms
import psutil
from loguru import logger
import gc

# Import background removal models
from rembg import remove as rembg_remove
from rembg import new_session

# Configuration
class Config:
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
    MODEL_CACHE_DIR = "models"
    TEMP_DIR = "temp"
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    MAX_IMAGE_DIMENSION = 4096
    RMBG_MODEL = "briaai/RMBG-2.0"

# Ensure directories exist
os.makedirs(Config.MODEL_CACHE_DIR, exist_ok=True)
os.makedirs(Config.TEMP_DIR, exist_ok=True)
os.makedirs("static", exist_ok=True)

# Pydantic models
class ProcessingOptions(BaseModel):
    model_type: str = Field(default="rmbg2", description="Model to use: rmbg2, rembg, isnet")
    enhance_edges: bool = Field(default=True, description="Apply edge enhancement")
    feather_amount: int = Field(default=2, ge=0, le=10, description="Edge feathering amount")
    alpha_matting: bool = Field(default=False, description="Apply alpha matting for better edges")
    post_process: bool = Field(default=True, description="Apply post-processing")

class ProcessingResult(BaseModel):
    processing_time: float
    model_used: str
    image_size: tuple
    memory_used: float

# Global model instances
class ModelManager:
    def __init__(self):
        self.rmbg2_model = None
        self.rembg_session = None
        self.device = Config.DEVICE
        logger.info(f"Initializing models on device: {self.device}")
    
    async def load_rmbg2(self):
        """Load RMBG 2.0 model"""
        if self.rmbg2_model is None:
            try:
                logger.info("Loading RMBG 2.0 model...")
                self.rmbg2_model = AutoModelForImageSegmentation.from_pretrained(
                    Config.RMBG_MODEL, 
                    trust_remote_code=True,
                    cache_dir=Config.MODEL_CACHE_DIR
                )
                torch.set_float32_matmul_precision(['high', 'highest'][0])
                self.rmbg2_model.to(self.device)
                self.rmbg2_model.eval()
                logger.info("RMBG 2.0 model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load RMBG 2.0: {e}")
                raise
    
    async def load_rembg(self):
        """Load rembg model"""
        if self.rembg_session is None:
            try:
                logger.info("Loading rembg model...")
                self.rembg_session = new_session('u2net')
                logger.info("rembg model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load rembg: {e}")
                raise
    
    def get_memory_usage(self):
        """Get current memory usage"""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024  # MB

model_manager = ModelManager()

# FastAPI app
app = FastAPI(
    title="AI Background Removal Service",
    description="Production-ready background removal API with RMBG 2.0 and advanced features",
    version="2.0.0"
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Utility functions
def validate_image(file: UploadFile) -> None:
    """Validate uploaded image file"""
    if file.size > Config.MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"File too large. Max size: {Config.MAX_FILE_SIZE // (1024*1024)}MB")
    
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in Config.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_ext}")

async def preprocess_image(image: Image.Image, max_size: int = 1024) -> tuple[Image.Image, tuple]:
    """Preprocess image for model input"""
    original_size = image.size
    
    # Convert to RGB if necessary
    if image.mode in ('RGBA', 'LA'):
        background = Image.new('RGB', image.size, (255, 255, 255))
        if image.mode == 'RGBA':
            background.paste(image, mask=image.split()[-1])
        else:
            background.paste(image)
        image = background
    elif image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Resize if too large
    if max(image.size) > max_size:
        image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    
    return image, original_size

def enhance_edges(mask: Image.Image, amount: int = 2) -> Image.Image:
    """Enhance mask edges using morphological operations"""
    if amount == 0:
        return mask
    
    # Convert to numpy for OpenCV operations
    mask_np = np.array(mask)
    
    # Apply morphological operations
    kernel = np.ones((amount, amount), np.uint8)
    mask_np = cv2.morphologyEx(mask_np, cv2.MORPH_CLOSE, kernel)
    mask_np = cv2.morphologyEx(mask_np, cv2.MORPH_OPEN, kernel)
    
    return Image.fromarray(mask_np)

def apply_feathering(mask: Image.Image, feather_amount: int = 2) -> Image.Image:
    """Apply feathering to mask edges"""
    if feather_amount == 0:
        return mask
    
    # Apply Gaussian blur for feathering
    return mask.filter(ImageFilter.GaussianBlur(radius=feather_amount))

def apply_alpha_matting(image: Image.Image, mask: Image.Image) -> Image.Image:
    """Apply alpha matting for better edge quality"""
    # Simple alpha matting implementation
    # In production, you might want to use more sophisticated methods
    mask_blur = mask.filter(ImageFilter.GaussianBlur(radius=1))
    
    # Create alpha channel from blurred mask
    image_rgba = image.convert('RGBA')
    image_rgba.putalpha(mask_blur)
    
    return image_rgba

async def remove_background_rmbg2(image: Image.Image) -> Image.Image:
    """Remove background using RMBG 2.0"""
    await model_manager.load_rmbg2()
    
    # Prepare transforms
    image_size = (1024, 1024)
    transform_image = transforms.Compose([
        transforms.Resize(image_size),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    
    # Transform image
    input_images = transform_image(image).unsqueeze(0).to(model_manager.device)
    
    # Prediction
    with torch.no_grad():
        preds = model_manager.rmbg2_model(input_images)[-1].sigmoid().cpu()
    
    pred = preds[0].squeeze()
    pred_pil = transforms.ToPILImage()(pred)
    mask = pred_pil.resize(image.size, Image.Resampling.LANCZOS)
    
    # Apply mask to image
    image.putalpha(mask)
    return image

async def remove_background_rembg(image: Image.Image) -> Image.Image:
    """Remove background using rembg"""
    await model_manager.load_rembg()
    
    # Convert to bytes
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    
    # Remove background
    result = rembg_remove(img_byte_arr, session=model_manager.rembg_session)
    
    # Convert back to PIL
    return Image.open(io.BytesIO(result))

async def process_image_with_options(
    image: Image.Image, 
    options: ProcessingOptions
) -> tuple[Image.Image, ProcessingResult]:
    """Process image with specified options"""
    start_time = time.time()
    start_memory = model_manager.get_memory_usage()
    
    # Preprocess
    processed_image, original_size = await preprocess_image(image)
    
    # Remove background based on model choice
    if options.model_type == "rmbg2":
        result_image = await remove_background_rmbg2(processed_image)
        model_used = "RMBG 2.0"
    elif options.model_type == "rembg":
        result_image = await remove_background_rembg(processed_image)
        model_used = "RemBG U2Net"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported model: {options.model_type}")
    
    # Post-processing
    if options.post_process and result_image.mode == 'RGBA':
        # Extract alpha channel for processing
        alpha = result_image.split()[-1]
        
        # Enhance edges
        if options.enhance_edges:
            alpha = enhance_edges(alpha, 2)
        
        # Apply feathering
        if options.feather_amount > 0:
            alpha = apply_feathering(alpha, options.feather_amount)
        
        # Apply alpha matting
        if options.alpha_matting:
            rgb_image = Image.new('RGB', result_image.size)
            rgb_image.paste(result_image, (0, 0), result_image)
            result_image = apply_alpha_matting(rgb_image, alpha)
        else:
            # Reapply processed alpha
            result_image.putalpha(alpha)
    
    # Resize back to original dimensions
    if result_image.size != original_size:
        result_image = result_image.resize(original_size, Image.Resampling.LANCZOS)
    
    processing_time = time.time() - start_time
    memory_used = model_manager.get_memory_usage() - start_memory
    
    # Cleanup
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    
    result = ProcessingResult(
        processing_time=processing_time,
        model_used=model_used,
        image_size=original_size,
        memory_used=memory_used
    )
    
    return result_image, result

# API Routes
@app.get("/")
async def home(request: Request):
    """Serve the main web interface"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "device": Config.DEVICE,
        "memory_usage_mb": model_manager.get_memory_usage(),
        "models_loaded": {
            "rmbg2": model_manager.rmbg2_model is not None,
            "rembg": model_manager.rembg_session is not None
        }
    }

@app.post("/remove-background")
async def remove_background_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    model_type: str = "rmbg2",
    enhance_edges: bool = True,
    feather_amount: int = 2,
    alpha_matting: bool = False,
    post_process: bool = True
):
    """
    Remove background from uploaded image
    
    - **file**: Image file (PNG, JPG, JPEG, WEBP)
    - **model_type**: Model to use (rmbg2, rembg)
    - **enhance_edges**: Apply edge enhancement
    - **feather_amount**: Edge feathering amount (0-10)
    - **alpha_matting**: Apply alpha matting
    - **post_process**: Apply post-processing
    """
    try:
        # Validate file
        validate_image(file)
        
        # Read image
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data))
        
        # Process image
        options = ProcessingOptions(
            model_type=model_type,
            enhance_edges=enhance_edges,
            feather_amount=feather_amount,
            alpha_matting=alpha_matting,
            post_process=post_process
        )
        
        result_image, processing_result = await process_image_with_options(image, options)
        
        # Convert to bytes
        img_byte_arr = io.BytesIO()
        result_image.save(img_byte_arr, format='PNG', optimize=True)
        img_byte_arr.seek(0)
        
        # Add processing info to headers
        headers = {
            "X-Processing-Time": str(processing_result.processing_time),
            "X-Model-Used": processing_result.model_used,
            "X-Image-Size": f"{processing_result.image_size[0]}x{processing_result.image_size[1]}",
            "X-Memory-Used": str(processing_result.memory_used)
        }
        
        return StreamingResponse(
            io.BytesIO(img_byte_arr.getvalue()),
            media_type="image/png",
            headers=headers,
            filename=f"bg_removed_{file.filename.rsplit('.', 1)[0]}.png"
        )
        
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/batch-remove-background")
async def batch_remove_background(
    files: List[UploadFile] = File(...),
    model_type: str = "rmbg2",
    enhance_edges: bool = True,
    feather_amount: int = 2,
    alpha_matting: bool = False,
    post_process: bool = True
):
    """
    Remove background from multiple images
    """
    if len(files) > 10:  # Limit batch size
        raise HTTPException(status_code=400, detail="Maximum 10 files per batch")
    
    results = []
    options = ProcessingOptions(
        model_type=model_type,
        enhance_edges=enhance_edges,
        feather_amount=feather_amount,
        alpha_matting=alpha_matting,
        post_process=post_process
    )
    
    for file in files:
        try:
            validate_image(file)
            image_data = await file.read()
            image = Image.open(io.BytesIO(image_data))
            
            result_image, processing_result = await process_image_with_options(image, options)
            
            # Convert to base64 for response
            img_byte_arr = io.BytesIO()
            result_image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            results.append({
                "filename": file.filename,
                "success": True,
                "processing_time": processing_result.processing_time,
                "model_used": processing_result.model_used,
                "size": f"{processing_result.image_size[0]}x{processing_result.image_size[1]}"
            })
            
        except Exception as e:
            logger.error(f"Error processing {file.filename}: {e}")
            results.append({
                "filename": file.filename,
                "success": False,
                "error": str(e)
            })
    
    return {"results": results}

@app.get("/models")
async def list_models():
    """List available models and their status"""
    return {
        "available_models": {
            "rmbg2": {
                "name": "BRIA RMBG 2.0",
                "description": "State-of-the-art background removal (90% accuracy)",
                "loaded": model_manager.rmbg2_model is not None
            },
            "rembg": {
                "name": "RemBG U2Net",
                "description": "Fast and reliable background removal",
                "loaded": model_manager.rembg_session is not None
            }
        },
        "recommended": "rmbg2"
    }

@app.post("/warmup")
async def warmup_models():
    """Warm up models by loading them into memory"""
    try:
        await model_manager.load_rmbg2()
        await model_manager.load_rembg()
        return {"status": "Models warmed up successfully"}
    except Exception as e:
        logger.error(f"Error warming up models: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        workers=1  # Single worker for model sharing
    )