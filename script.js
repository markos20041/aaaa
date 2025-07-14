function generatePassword() {
  const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()";
  let password = "";
  for (let i = 0; i < 12; i++) {
    password += chars[Math.floor(Math.random() * chars.length)];
  }
  document.getElementById("passwordOutput").innerText = password;
}

function calculate() {
  const input = document.getElementById("calcInput").value;
  try {
    const result = eval(input);
    document.getElementById("calcOutput").innerText = "�������: " + result;
  } catch {
    document.getElementById("calcOutput").innerText = "��� �� ������!";
  }
}

function showColor() {
  const color = document.getElementById("colorPicker").value;
  const output = document.getElementById("colorOutput");
  output.innerText = "����� �������: " + color;
  output.style.background = color;
  output.style.color = "#fff";
}

function reverseText() {
  const input = document.getElementById("reverseInput").value;
  document.getElementById("reverseOutput").innerText = input.split("").reverse().join("");
}

function convertToBase64() {
  const input = document.getElementById("base64Input").value;
  const encoded = btoa(input);
  document.getElementById("base64Output").innerText = encoded;
}

function countWords() {
  const text = document.getElementById("wordCountInput").value.trim();
  const wordCount = text === "" ? 0 : text.split(/\s+/).length;
  document.getElementById("wordCountOutput").innerText = "��� �������: " + wordCount;
}

function updateClock() {
  const now = new Date();
  const time = now.toLocaleTimeString();
  document.getElementById("clockOutput").innerText = time;
}

setInterval(updateClock, 1000);
updateClock();

class BackgroundRemovalApp {
    constructor() {
        this.apiBase = 'http://localhost:5000/api';
        this.currentImage = null;
        this.processedImage = null;
        this.currentResultId = null;
        this.canvas = null;
        this.ctx = null;
        this.isDrawing = false;
        this.currentTool = 'brush';
        this.brushSize = 10;
        this.currentBackground = 'transparent';
        
        this.init();
    }

    init() {
        this.initializeElements();
        this.setupEventListeners();
        this.setupDragAndDrop();
        this.setupCanvas();
        this.loadAvailableModels();
    }

    initializeElements() {
        // Upload elements
        this.uploadArea = document.getElementById('uploadArea');
        this.uploadContainer = document.getElementById('uploadContainer');
        this.imageInput = document.getElementById('imageInput');
        this.optionsPanel = document.getElementById('optionsPanel');
        
        // Processing options
        this.modelSelect = document.getElementById('modelSelect');
        this.qualitySelect = document.getElementById('qualitySelect');
        this.featherSlider = document.getElementById('featherSlider');
        this.featherValue = document.getElementById('featherValue');
        this.asyncProcess = document.getElementById('asyncProcess');
        this.processBtn = document.getElementById('processBtn');
        
        // Preview elements
        this.previewSection = document.getElementById('previewSection');
        this.originalImage = document.getElementById('originalImage');
        this.resultCanvas = document.getElementById('resultCanvas');
        this.processingOverlay = document.getElementById('processingOverlay');
        this.processingText = document.getElementById('processingText');
        
        // Editor tools
        this.editorTools = document.getElementById('editorTools');
        this.brushTool = document.getElementById('brushTool');
        this.eraserTool = document.getElementById('eraserTool');
        this.zoomTool = document.getElementById('zoomTool');
        this.brushSize = document.getElementById('brushSize');
        this.brushSizeValue = document.getElementById('brushSizeValue');
        
        // Background options
        this.bgPresets = document.querySelectorAll('.bg-preset');
        this.customBgColor = document.getElementById('customBgColor');
        
        // Export elements
        this.exportSection = document.getElementById('exportSection');
        this.downloadPNG = document.getElementById('downloadPNG');
        this.downloadJPG = document.getElementById('downloadJPG');
        this.downloadWebP = document.getElementById('downloadWebP');
        
        // Modal and toast elements
        this.loadingModal = document.getElementById('loadingModal');
        this.loadingText = document.getElementById('loadingText');
        this.progressFill = document.getElementById('progressFill');
        this.errorToast = document.getElementById('errorToast');
        this.successToast = document.getElementById('successToast');
        this.errorMessage = document.getElementById('errorMessage');
        this.successMessage = document.getElementById('successMessage');
    }

    setupEventListeners() {
        // Upload listeners
        this.uploadArea.addEventListener('click', () => this.imageInput.click());
        this.imageInput.addEventListener('change', this.handleFileSelect.bind(this));
        
        // Processing listeners
        this.featherSlider.addEventListener('input', this.updateFeatherValue.bind(this));
        this.processBtn.addEventListener('click', this.processImage.bind(this));
        
        // Tool listeners
        this.brushTool.addEventListener('click', () => this.setTool('brush'));
        this.eraserTool.addEventListener('click', () => this.setTool('eraser'));
        this.zoomTool.addEventListener('click', () => this.setTool('zoom'));
        this.brushSize.addEventListener('input', this.updateBrushSize.bind(this));
        
        // Background preset listeners
        this.bgPresets.forEach(preset => {
            preset.addEventListener('click', () => this.setBackground(preset.dataset.bg));
        });
        this.customBgColor.addEventListener('change', () => this.setBackground('custom'));
        
        // Export listeners
        this.downloadPNG.addEventListener('click', () => this.downloadImage('png'));
        this.downloadJPG.addEventListener('click', () => this.downloadImage('jpg'));
        this.downloadWebP.addEventListener('click', () => this.downloadImage('webp'));
        
        // Toast close listeners
        document.querySelectorAll('.toast-close').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.target.closest('.toast').style.display = 'none';
            });
        });
    }

    setupDragAndDrop() {
        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            this.uploadArea.addEventListener(eventName, this.preventDefaults, false);
            document.body.addEventListener(eventName, this.preventDefaults, false);
        });

        // Highlight drop area when item is dragged over it
        ['dragenter', 'dragover'].forEach(eventName => {
            this.uploadArea.addEventListener(eventName, () => {
                this.uploadArea.classList.add('dragover');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            this.uploadArea.addEventListener(eventName, () => {
                this.uploadArea.classList.remove('dragover');
            }, false);
        });

        // Handle dropped files
        this.uploadArea.addEventListener('drop', this.handleDrop.bind(this), false);
    }

    setupCanvas() {
        this.canvas = this.resultCanvas;
        this.ctx = this.canvas.getContext('2d');
        
        // Canvas mouse events for editing
        this.canvas.addEventListener('mousedown', this.startDrawing.bind(this));
        this.canvas.addEventListener('mousemove', this.draw.bind(this));
        this.canvas.addEventListener('mouseup', this.stopDrawing.bind(this));
        this.canvas.addEventListener('mouseout', this.stopDrawing.bind(this));
    }

    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length > 0) {
            this.handleFile(files[0]);
        }
    }

    handleFileSelect(e) {
        const file = e.target.files[0];
        if (file) {
            this.handleFile(file);
        }
    }

    handleFile(file) {
        // Validate file type
        const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'];
        if (!allowedTypes.includes(file.type)) {
            this.showError('Please select a PNG, JPG, JPEG, or WebP image file.');
            return;
        }

        // Validate file size (16MB max)
        if (file.size > 16 * 1024 * 1024) {
            this.showError('File size must be less than 16MB.');
            return;
        }

        this.currentImage = file;
        this.displayOriginalImage(file);
        this.optionsPanel.style.display = 'block';
        this.resetUI();
    }

    displayOriginalImage(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            this.originalImage.src = e.target.result;
            this.originalImage.onload = () => {
                this.previewSection.style.display = 'block';
                this.setupCanvas();
            };
        };
        reader.readAsDataURL(file);
    }

    resetUI() {
        this.editorTools.style.display = 'none';
        this.exportSection.style.display = 'none';
        this.processingOverlay.style.display = 'none';
        this.currentResultId = null;
        this.processedImage = null;
    }

    updateFeatherValue() {
        const value = this.featherSlider.value;
        this.featherValue.textContent = `${value}px`;
    }

    updateBrushSize() {
        const value = this.brushSize.value;
        this.brushSizeValue.textContent = value;
    }

    setTool(tool) {
        this.currentTool = tool;
        document.querySelectorAll('.tool-btn').forEach(btn => btn.classList.remove('active'));
        document.getElementById(`${tool}Tool`).classList.add('active');
        
        // Update cursor
        if (tool === 'brush' || tool === 'eraser') {
            this.canvas.style.cursor = 'crosshair';
        } else if (tool === 'zoom') {
            this.canvas.style.cursor = 'zoom-in';
        }
    }

    setBackground(bgType) {
        this.currentBackground = bgType;
        document.querySelectorAll('.bg-preset').forEach(preset => preset.classList.remove('active'));
        document.querySelector(`[data-bg="${bgType}"]`).classList.add('active');
        
        if (this.processedImage) {
            this.updateCanvasBackground();
        }
    }

    updateCanvasBackground() {
        if (!this.processedImage) return;
        
        const canvas = this.canvas;
        const ctx = this.ctx;
        
        // Clear canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Set background
        if (this.currentBackground === 'transparent') {
            // Draw checkerboard pattern for transparency
            this.drawCheckerboard(ctx, canvas.width, canvas.height);
        } else if (this.currentBackground === 'white') {
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
        } else if (this.currentBackground === 'black') {
            ctx.fillStyle = '#000000';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
        } else if (this.currentBackground === 'custom') {
            ctx.fillStyle = this.customBgColor.value;
            ctx.fillRect(0, 0, canvas.width, canvas.height);
        }
        
        // Draw the processed image
        ctx.drawImage(this.processedImage, 0, 0);
    }

    drawCheckerboard(ctx, width, height) {
        const size = 20;
        ctx.fillStyle = '#f7fafc';
        ctx.fillRect(0, 0, width, height);
        
        ctx.fillStyle = '#e2e8f0';
        for (let x = 0; x < width; x += size) {
            for (let y = 0; y < height; y += size) {
                if ((x / size + y / size) % 2) {
                    ctx.fillRect(x, y, size, size);
                }
            }
        }
    }

    async loadAvailableModels() {
        try {
            const response = await fetch(`${this.apiBase}/models`);
            const data = await response.json();
            
            // Update model select options
            this.modelSelect.innerHTML = '<option value="auto">Auto-detect (Recommended)</option>';
            data.models.forEach(model => {
                const option = document.createElement('option');
                option.value = model;
                option.textContent = data.descriptions[model] || model;
                this.modelSelect.appendChild(option);
            });
        } catch (error) {
            console.warn('Could not load model information:', error);
        }
    }

    async processImage() {
        if (!this.currentImage) {
            this.showError('Please select an image first.');
            return;
        }

        this.processBtn.disabled = true;
        this.processingOverlay.style.display = 'flex';
        this.processingText.textContent = 'Uploading and processing...';

        const formData = new FormData();
        formData.append('image', this.currentImage);
        formData.append('model', this.modelSelect.value);
        formData.append('quality', this.qualitySelect.value);
        formData.append('feather_radius', this.featherSlider.value);
        formData.append('async', this.asyncProcess.checked.toString());

        try {
            const response = await fetch(`${this.apiBase}/remove-background`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.error) {
                throw new Error(result.error);
            }

            if (result.status === 'processing') {
                this.processingText.textContent = 'Processing in background...';
                this.pollTaskStatus(result.task_id);
            } else if (result.status === 'completed') {
                this.currentResultId = result.result_id;
                await this.loadProcessedImage();
                this.showSuccess('Background removed successfully!');
            }

        } catch (error) {
            this.showError(`Processing failed: ${error.message}`);
            this.processingOverlay.style.display = 'none';
            this.processBtn.disabled = false;
        }
    }

    async pollTaskStatus(taskId) {
        const pollInterval = setInterval(async () => {
            try {
                const response = await fetch(`${this.apiBase}/status/${taskId}`);
                const result = await response.json();

                if (result.status === 'completed') {
                    clearInterval(pollInterval);
                    this.currentResultId = result.result_id;
                    await this.loadProcessedImage();
                    this.showSuccess('Background removed successfully!');
                } else if (result.status === 'error') {
                    clearInterval(pollInterval);
                    throw new Error(result.error || 'Processing failed');
                }
                // Continue polling if status is 'processing'
            } catch (error) {
                clearInterval(pollInterval);
                this.showError(`Processing failed: ${error.message}`);
                this.processingOverlay.style.display = 'none';
                this.processBtn.disabled = false;
            }
        }, 2000); // Poll every 2 seconds
    }

    async loadProcessedImage() {
        try {
            const response = await fetch(`${this.apiBase}/preview/${this.currentResultId}`);
            const blob = await response.blob();
            const imageUrl = URL.createObjectURL(blob);

            const img = new Image();
            img.onload = () => {
                this.processedImage = img;
                this.setupResultCanvas(img);
                this.processingOverlay.style.display = 'none';
                this.processBtn.disabled = false;
                this.editorTools.style.display = 'block';
                this.exportSection.style.display = 'block';
                URL.revokeObjectURL(imageUrl);
            };
            img.src = imageUrl;

        } catch (error) {
            this.showError(`Failed to load processed image: ${error.message}`);
            this.processingOverlay.style.display = 'none';
            this.processBtn.disabled = false;
        }
    }

    setupResultCanvas(img) {
        this.canvas.width = img.width;
        this.canvas.height = img.height;
        this.updateCanvasBackground();
    }

    // Canvas drawing methods
    startDrawing(e) {
        if (this.currentTool === 'zoom') {
            // Implement zoom functionality
            return;
        }

        this.isDrawing = true;
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        this.draw(e);
    }

    draw(e) {
        if (!this.isDrawing || this.currentTool === 'zoom') return;

        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        this.ctx.lineWidth = this.brushSize.value;
        this.ctx.lineCap = 'round';

        if (this.currentTool === 'brush') {
            this.ctx.globalCompositeOperation = 'source-over';
            this.ctx.strokeStyle = 'rgba(255, 255, 255, 1)';
        } else if (this.currentTool === 'eraser') {
            this.ctx.globalCompositeOperation = 'destination-out';
        }

        this.ctx.lineTo(x, y);
        this.ctx.stroke();
        this.ctx.beginPath();
        this.ctx.moveTo(x, y);
    }

    stopDrawing() {
        if (this.isDrawing) {
            this.isDrawing = false;
            this.ctx.beginPath();
        }
    }

    async downloadImage(format) {
        if (!this.currentResultId) {
            this.showError('No processed image to download.');
            return;
        }

        try {
            let downloadUrl;
            let filename;

            if (format === 'png') {
                // Download the original PNG with transparency
                downloadUrl = `${this.apiBase}/download/${this.currentResultId}`;
                filename = `background_removed_${Date.now()}.png`;
            } else {
                // For JPG and WebP, we need to create a composite image with background
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                canvas.width = this.processedImage.width;
                canvas.height = this.processedImage.height;

                // Add background
                if (this.currentBackground === 'white') {
                    ctx.fillStyle = '#ffffff';
                } else if (this.currentBackground === 'black') {
                    ctx.fillStyle = '#000000';
                } else if (this.currentBackground === 'custom') {
                    ctx.fillStyle = this.customBgColor.value;
                } else {
                    ctx.fillStyle = '#ffffff'; // Default to white for non-transparent formats
                }
                ctx.fillRect(0, 0, canvas.width, canvas.height);

                // Draw the processed image
                ctx.drawImage(this.processedImage, 0, 0);

                // Convert to blob and download
                canvas.toBlob((blob) => {
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `background_removed_${Date.now()}.${format}`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                }, `image/${format}`, 0.9);

                this.showSuccess(`Image downloaded as ${format.toUpperCase()}`);
                return;
            }

            // Download PNG directly from server
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            
            this.showSuccess('Image downloaded successfully!');

        } catch (error) {
            this.showError(`Download failed: ${error.message}`);
        }
    }

    showError(message) {
        this.errorMessage.textContent = message;
        this.errorToast.style.display = 'flex';
        setTimeout(() => {
            this.errorToast.style.display = 'none';
        }, 5000);
    }

    showSuccess(message) {
        this.successMessage.textContent = message;
        this.successToast.style.display = 'flex';
        setTimeout(() => {
            this.successToast.style.display = 'none';
        }, 3000);
    }

    showLoading(message = 'Processing...') {
        this.loadingText.textContent = message;
        this.loadingModal.style.display = 'flex';
    }

    hideLoading() {
        this.loadingModal.style.display = 'none';
    }

    updateProgress(percentage) {
        this.progressFill.style.width = `${percentage}%`;
    }
}

// Enhanced utility functions
class ImageUtils {
    static async resizeImage(file, maxWidth = 1024, maxHeight = 1024) {
        return new Promise((resolve) => {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            const img = new Image();

            img.onload = () => {
                let { width, height } = img;

                // Calculate new dimensions
                if (width > height) {
                    if (width > maxWidth) {
                        height = (height * maxWidth) / width;
                        width = maxWidth;
                    }
                } else {
                    if (height > maxHeight) {
                        width = (width * maxHeight) / height;
                        height = maxHeight;
                    }
                }

                canvas.width = width;
                canvas.height = height;

                ctx.drawImage(img, 0, 0, width, height);
                
                canvas.toBlob(resolve, file.type, 0.9);
            };

            img.src = URL.createObjectURL(file);
        });
    }

    static async compressImage(file, quality = 0.8) {
        return new Promise((resolve) => {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            const img = new Image();

            img.onload = () => {
                canvas.width = img.width;
                canvas.height = img.height;
                ctx.drawImage(img, 0, 0);
                canvas.toBlob(resolve, 'image/jpeg', quality);
            };

            img.src = URL.createObjectURL(file);
        });
    }

    static getImageDimensions(file) {
        return new Promise((resolve) => {
            const img = new Image();
            img.onload = () => {
                resolve({ width: img.width, height: img.height });
                URL.revokeObjectURL(img.src);
            };
            img.src = URL.createObjectURL(file);
        });
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.bgRemovalApp = new BackgroundRemovalApp();
});

// Add keyboard shortcuts
document.addEventListener('keydown', (e) => {
    if (window.bgRemovalApp && e.ctrlKey) {
        switch (e.key) {
            case 's':
                e.preventDefault();
                if (window.bgRemovalApp.currentResultId) {
                    window.bgRemovalApp.downloadImage('png');
                }
                break;
            case 'z':
                e.preventDefault();
                // Implement undo functionality
                break;
            case 'y':
                e.preventDefault();
                // Implement redo functionality
                break;
        }
    }
});

// Handle window resize for responsive canvas
window.addEventListener('resize', () => {
    if (window.bgRemovalApp && window.bgRemovalApp.processedImage) {
        // Recalculate canvas size if needed
        setTimeout(() => {
            window.bgRemovalApp.updateCanvasBackground();
        }, 100);
    }
});
