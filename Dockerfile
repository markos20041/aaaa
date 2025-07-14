# Use NVIDIA's PyTorch base image for GPU support
FROM nvidia/cuda:11.8-devel-ubuntu20.04 as base

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV MODEL_CACHE_DIR=/app/models

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cu118 && \
    pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p uploads outputs models templates

# Download model weights (optional - can be done at runtime)
# RUN python3 -c "from transformers import AutoModelForImageSegmentation; AutoModelForImageSegmentation.from_pretrained('briaai/RMBG-2.0', trust_remote_code=True, cache_dir='/app/models')"

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Run the application
CMD ["python3", "app.py"]

# Alternative: CPU-only version
FROM python:3.10-slim as cpu-only

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV MODEL_CACHE_DIR=/app/models

RUN apt-get update && apt-get install -y \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgl1-mesa-glx \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p uploads outputs models templates

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

CMD ["python3", "app.py"]