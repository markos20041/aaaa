class BackgroundRemovalTool {
    constructor() {
        this.API_BASE = 'http://localhost:5000/api';
        this.currentImage = null;
        this.resultImage = null;
        this.isProcessing = false;
        this.editMode = false;
        this.canvas = null;
        this.ctx = null;
        this.isDrawing = false;
        this.currentTool = 'brush';
        this.brushSize = 15;
        
        this.initializeElements();
        this.setupEventListeners();
        this.showSection('upload');
    }
    
    initializeElements() {
        // Main sections
        this.uploadSection = document.getElementById('uploadSection');
        this.settingsSection = document.getElementById('settingsSection');
        this.previewSection = document.getElementById('previewSection');
        this.loadingSection = document.getElementById('loadingSection');
        this.editSection = document.getElementById('editSection');
        
        // Upload elements
        this.uploadArea = document.getElementById('uploadArea');
        this.uploadBtn = document.getElementById('uploadBtn');
        this.fileInput = document.getElementById('fileInput');
        
        // Settings elements
        this.modelSelect = document.getElementById('modelSelect');
        this.enhanceEdges = document.getElementById('enhanceEdges');
        this.alphaMatting = document.getElementById('alphaMatting');
        this.processBtn = document.getElementById('processBtn');
        
        // Preview elements
        this.originalImage = document.getElementById('originalImage');
        this.resultImage = document.getElementById('resultImage');
        this.downloadBtn = document.getElementById('downloadBtn');
        this.newImageBtn = document.getElementById('newImageBtn');
        this.editBtn = document.getElementById('editBtn');
        this.statsCard = document.getElementById('statsCard');
        
        // Stats elements
        this.processingTime = document.getElementById('processingTime');
        this.modelUsed = document.getElementById('modelUsed');
        this.imageSize = document.getElementById('imageSize');
        
        // Loading elements
        this.loadingText = document.getElementById('loadingText');
        this.progressFill = document.getElementById('progressFill');
        
        // Edit elements
        this.brushTool = document.getElementById('brushTool');
        this.eraseTool = document.getElementById('eraseTool');
        this.brushSize = document.getElementById('brushSize');
        this.brushSizeValue = document.getElementById('brushSizeValue');
        this.editCanvas = document.getElementById('editCanvas');
        this.applyEdits = document.getElementById('applyEdits');
        this.cancelEdits = document.getElementById('cancelEdits');
    }
    
    setupEventListeners() {
        // Upload listeners
        this.uploadBtn.addEventListener('click', () => this.fileInput.click());
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        this.uploadArea.addEventListener('click', () => this.fileInput.click());
        
        // Drag and drop
        this.uploadArea.addEventListener('dragover', (e) => this.handleDragOver(e));
        this.uploadArea.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        this.uploadArea.addEventListener('drop', (e) => this.handleDrop(e));
        
        // Process button
        this.processBtn.addEventListener('click', () => this.processImage());
        
        // Result actions
        this.downloadBtn.addEventListener('click', () => this.downloadResult());
        this.newImageBtn.addEventListener('click', () => this.resetTool());
        this.editBtn.addEventListener('click', () => this.enterEditMode());
        
        // Edit tools
        this.brushTool.addEventListener('click', () => this.setEditTool('brush'));
        this.eraseTool.addEventListener('click', () => this.setEditTool('erase'));
        this.brushSize.addEventListener('input', (e) => this.updateBrushSize(e.target.value));
        this.applyEdits.addEventListener('click', () => this.applyEdits());
        this.cancelEdits.addEventListener('click', () => this.exitEditMode());
        
        // Canvas editing (will be set up when entering edit mode)
    }
    
    showSection(section) {
        // Hide all sections
        this.uploadSection.style.display = 'none';
        this.settingsSection.style.display = 'none';
        this.previewSection.style.display = 'none';
        this.loadingSection.style.display = 'none';
        this.editSection.style.display = 'none';
        
        // Show requested section
        switch(section) {
            case 'upload':
                this.uploadSection.style.display = 'block';
                break;
            case 'settings':
                this.settingsSection.style.display = 'block';
                break;
            case 'preview':
                this.previewSection.style.display = 'block';
                break;
            case 'loading':
                this.loadingSection.style.display = 'block';
                break;
            case 'edit':
                this.editSection.style.display = 'block';
                break;
        }
    }
    
    handleDragOver(e) {
        e.preventDefault();
        this.uploadArea.classList.add('drag-over');
    }
    
    handleDragLeave(e) {
        e.preventDefault();
        this.uploadArea.classList.remove('drag-over');
    }
    
    handleDrop(e) {
        e.preventDefault();
        this.uploadArea.classList.remove('drag-over');
        
        const files = e.dataTransfer.files;
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
        // Validate file
        if (!this.validateFile(file)) {
            return;
        }
        
        // Store file and create preview
        this.currentImage = file;
        
        const reader = new FileReader();
        reader.onload = (e) => {
            this.originalImage.src = e.target.result;
            this.showSection('settings');
            this.uploadSection.classList.add('fade-in');
        };
        reader.readAsDataURL(file);
    }
    
    validateFile(file) {
        const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'];
        const maxSize = 16 * 1024 * 1024; // 16MB
        
        if (!allowedTypes.includes(file.type)) {
            this.showError('Please select a valid image file (PNG, JPG, JPEG, or WEBP)');
            return false;
        }
        
        if (file.size > maxSize) {
            this.showError('File size must be less than 16MB');
            return false;
        }
        
        return true;
    }
    
    async processImage() {
        if (!this.currentImage || this.isProcessing) {
            return;
        }
        
        this.isProcessing = true;
        this.showSection('loading');
        this.startProgressAnimation();
        
        try {
            const formData = new FormData();
            formData.append('image', this.currentImage);
            formData.append('model', this.modelSelect.value);
            formData.append('enhance_edges', this.enhanceEdges.checked.toString());
            formData.append('alpha_matting', this.alphaMatting.checked.toString());
            
            const response = await fetch(`${this.API_BASE}/remove-background`, {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.handleProcessingSuccess(result);
            } else {
                throw new Error(result.error || 'Processing failed');
            }
            
        } catch (error) {
            this.handleProcessingError(error);
        } finally {
            this.isProcessing = false;
            this.stopProgressAnimation();
        }
    }
    
    handleProcessingSuccess(result) {
        // Set result image
        this.resultImage.src = result.image;
        this.resultImageData = result.image;
        
        // Update stats
        this.processingTime.textContent = `${result.processing_time}s`;
        this.modelUsed.textContent = result.model_used;
        this.imageSize.textContent = `${result.image_size[0]} × ${result.image_size[1]}`;
        
        // Show results
        this.showSection('preview');
        this.statsCard.style.display = 'block';
        this.previewSection.classList.add('slide-up');
        
        this.showSuccess('Background removed successfully!');
    }
    
    handleProcessingError(error) {
        console.error('Processing error:', error);
        this.showError(`Failed to process image: ${error.message}`);
        this.showSection('settings');
    }
    
    startProgressAnimation() {
        this.progressFill.style.width = '0%';
        let progress = 0;
        
        this.progressInterval = setInterval(() => {
            progress += Math.random() * 10;
            if (progress > 90) progress = 90;
            this.progressFill.style.width = `${progress}%`;
        }, 200);
        
        // Update loading text
        const messages = [
            'Analyzing image structure...',
            'Detecting subject boundaries...',
            'Applying AI magic...',
            'Refining edges...',
            'Almost done...'
        ];
        
        let messageIndex = 0;
        this.messageInterval = setInterval(() => {
            this.loadingText.textContent = messages[messageIndex];
            messageIndex = (messageIndex + 1) % messages.length;
        }, 1500);
    }
    
    stopProgressAnimation() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
            this.progressFill.style.width = '100%';
        }
        
        if (this.messageInterval) {
            clearInterval(this.messageInterval);
        }
    }
    
    downloadResult() {
        if (!this.resultImageData) {
            this.showError('No result to download');
            return;
        }
        
        // Convert base64 to blob and download
        const link = document.createElement('a');
        link.href = this.resultImageData;
        link.download = `background-removed-${Date.now()}.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        this.showSuccess('Image downloaded successfully!');
    }
    
    resetTool() {
        this.currentImage = null;
        this.resultImage = null;
        this.resultImageData = null;
        this.fileInput.value = '';
        this.statsCard.style.display = 'none';
        this.showSection('upload');
    }
    
    enterEditMode() {
        if (!this.resultImageData) {
            this.showError('No result image to edit');
            return;
        }
        
        this.showSection('edit');
        this.setupEditCanvas();
        this.editMode = true;
    }
    
    setupEditCanvas() {
        this.canvas = this.editCanvas;
        this.ctx = this.canvas.getContext('2d');
        
        // Load result image onto canvas
        const img = new Image();
        img.onload = () => {
            this.canvas.width = img.width;
            this.canvas.height = img.height;
            this.ctx.drawImage(img, 0, 0);
            this.canvas.style.display = 'block';
        };
        img.src = this.resultImageData;
        
        // Setup canvas event listeners
        this.canvas.addEventListener('mousedown', (e) => this.startDrawing(e));
        this.canvas.addEventListener('mousemove', (e) => this.draw(e));
        this.canvas.addEventListener('mouseup', () => this.stopDrawing());
        this.canvas.addEventListener('mouseout', () => this.stopDrawing());
        
        // Touch events for mobile
        this.canvas.addEventListener('touchstart', (e) => this.startDrawing(e.touches[0]));
        this.canvas.addEventListener('touchmove', (e) => {
            e.preventDefault();
            this.draw(e.touches[0]);
        });
        this.canvas.addEventListener('touchend', () => this.stopDrawing());
    }
    
    setEditTool(tool) {
        this.currentTool = tool;
        this.brushTool.classList.toggle('active', tool === 'brush');
        this.eraseTool.classList.toggle('active', tool === 'erase');
    }
    
    updateBrushSize(size) {
        this.brushSize = size;
        this.brushSizeValue.textContent = `${size}px`;
    }
    
    startDrawing(e) {
        this.isDrawing = true;
        this.draw(e);
    }
    
    draw(e) {
        if (!this.isDrawing) return;
        
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        this.ctx.lineWidth = this.brushSize;
        this.ctx.lineCap = 'round';
        
        if (this.currentTool === 'brush') {
            this.ctx.globalCompositeOperation = 'source-over';
            this.ctx.strokeStyle = 'rgba(255, 255, 255, 1)';
        } else if (this.currentTool === 'erase') {
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
    
    applyEdits() {
        // Convert canvas to data URL
        this.resultImageData = this.canvas.toDataURL('image/png');
        this.resultImage.src = this.resultImageData;
        
        this.exitEditMode();
        this.showSuccess('Edits applied successfully!');
    }
    
    exitEditMode() {
        this.editMode = false;
        this.canvas = null;
        this.ctx = null;
        this.editCanvas.style.display = 'none';
        this.showSection('preview');
    }
    
    showError(message) {
        this.showNotification(message, 'error');
    }
    
    showSuccess(message) {
        this.showNotification(message, 'success');
    }
    
    showNotification(message, type) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        // Style the notification
        Object.assign(notification.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            padding: '15px 20px',
            borderRadius: '8px',
            color: 'white',
            fontWeight: '600',
            zIndex: '10000',
            maxWidth: '400px',
            wordWrap: 'break-word',
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
            transform: 'translateX(400px)',
            transition: 'transform 0.3s ease'
        });
        
        if (type === 'error') {
            notification.style.background = 'linear-gradient(135deg, #ff4757, #ff3838)';
        } else {
            notification.style.background = 'linear-gradient(135deg, #2ed573, #1e90ff)';
        }
        
        // Add to page
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 100);
        
        // Remove after delay
        setTimeout(() => {
            notification.style.transform = 'translateX(400px)';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 4000);
    }
    
    // Health check method
    async checkServerHealth() {
        try {
            const response = await fetch(`${this.API_BASE}/health`);
            const result = await response.json();
            
            if (result.status === 'healthy') {
                console.log('Backend server is healthy');
                console.log('Available models:', result.models);
                return true;
            }
        } catch (error) {
            console.warn('Backend server not available:', error.message);
            this.showError('Backend server is not available. Please make sure the Python server is running.');
            return false;
        }
    }
}

// Initialize the tool when page loads
document.addEventListener('DOMContentLoaded', () => {
    const tool = new BackgroundRemovalTool();
    
    // Check server health on startup
    tool.checkServerHealth();
    
    // Expose tool globally for debugging
    window.backgroundTool = tool;
});
