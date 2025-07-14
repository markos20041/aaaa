// Background Removal Tool - Frontend JavaScript
class BackgroundRemovalTool {
    constructor() {
        this.apiBase = 'http://localhost:5000/api';
        this.currentFileId = null;
        this.currentTool = null;
        this.brushSize = 15;
        this.edits = [];
        this.isEditing = false;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.checkAPIHealth();
    }
    
    setupEventListeners() {
        // File upload handlers
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const browseLink = document.querySelector('.browse-link');
        
        // Drag and drop
        uploadArea.addEventListener('dragover', this.handleDragOver.bind(this));
        uploadArea.addEventListener('dragleave', this.handleDragLeave.bind(this));
        uploadArea.addEventListener('drop', this.handleDrop.bind(this));
        
        // Click to browse
        uploadArea.addEventListener('click', () => fileInput.click());
        browseLink.addEventListener('click', (e) => {
            e.stopPropagation();
            fileInput.click();
        });
        
        // File input change
        fileInput.addEventListener('change', this.handleFileSelect.bind(this));
        
        // Edit tools
        const brushTool = document.getElementById('brushTool');
        const eraserTool = document.getElementById('eraserTool');
        const brushSize = document.getElementById('brushSize');
        const brushSizeValue = document.getElementById('brushSizeValue');
        const resetEdits = document.getElementById('resetEdits');
        const applyEdits = document.getElementById('applyEdits');
        
        if (brushTool) brushTool.addEventListener('click', () => this.selectTool('add'));
        if (eraserTool) eraserTool.addEventListener('click', () => this.selectTool('remove'));
        if (brushSize) {
            brushSize.addEventListener('input', (e) => {
                this.brushSize = parseInt(e.target.value);
                brushSizeValue.textContent = `${this.brushSize}px`;
            });
        }
        if (resetEdits) resetEdits.addEventListener('click', this.resetEdits.bind(this));
        if (applyEdits) applyEdits.addEventListener('click', this.applyEdits.bind(this));
        
        // Action buttons
        const downloadBtn = document.getElementById('downloadBtn');
        const processAnother = document.getElementById('processAnother');
        const tryAgainBtn = document.getElementById('tryAgainBtn');
        
        if (downloadBtn) downloadBtn.addEventListener('click', this.downloadResult.bind(this));
        if (processAnother) processAnother.addEventListener('click', this.processAnother.bind(this));
        if (tryAgainBtn) tryAgainBtn.addEventListener('click', this.processAnother.bind(this));
        
        // Result image editing
        const resultImage = document.getElementById('resultImage');
        if (resultImage) {
            resultImage.addEventListener('mousedown', this.startEditing.bind(this));
            resultImage.addEventListener('mousemove', this.continueEditing.bind(this));
            resultImage.addEventListener('mouseup', this.stopEditing.bind(this));
            resultImage.addEventListener('mouseleave', this.stopEditing.bind(this));
        }
    }
    
    async checkAPIHealth() {
        try {
            const response = await fetch(`${this.apiBase}/health`);
            const data = await response.json();
            if (data.status === 'healthy') {
                console.log('API is healthy', data);
            }
        } catch (error) {
            console.error('API health check failed:', error);
            this.showError('Unable to connect to the processing server. Please try again later.');
        }
    }
    
    // File handling methods
    handleDragOver(e) {
        e.preventDefault();
        document.getElementById('uploadArea').classList.add('dragover');
    }
    
    handleDragLeave(e) {
        e.preventDefault();
        document.getElementById('uploadArea').classList.remove('dragover');
    }
    
    handleDrop(e) {
        e.preventDefault();
        document.getElementById('uploadArea').classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            this.processFile(files[0]);
        }
    }
    
    handleFileSelect(e) {
        const file = e.target.files[0];
        if (file) {
            this.processFile(file);
        }
    }
    
    validateFile(file) {
        const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png'];
        const maxSize = 16 * 1024 * 1024; // 16MB
        
        if (!allowedTypes.includes(file.type)) {
            this.showError('Please select a valid image file (JPG, JPEG, or PNG).');
            return false;
        }
        
        if (file.size > maxSize) {
            this.showError('File size must be less than 16MB.');
            return false;
        }
        
        return true;
    }
    
    async processFile(file) {
        if (!this.validateFile(file)) return;
        
        // Show processing section
        this.showSection('processingSection');
        
        // Create FormData
        const formData = new FormData();
        formData.append('image', file);
        
        // Get selected model
        const selectedModel = document.querySelector('input[name="model"]:checked')?.value || 'general';
        formData.append('model', selectedModel);
        
        // Get enhance edges option
        const enhanceEdges = document.getElementById('enhanceEdges')?.checked || true;
        formData.append('enhance_edges', enhanceEdges.toString());
        
        try {
            // Show progress animation
            this.animateProgress();
            
            const response = await fetch(`${this.apiBase}/upload`, {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.currentFileId = data.file_id;
                
                // Load and display results
                await this.loadResults(data);
                
                // Show success animation
                this.showSuccessMessage();
            } else {
                throw new Error(data.error || 'Processing failed');
            }
            
        } catch (error) {
            console.error('Processing error:', error);
            this.showError(error.message || 'Failed to process image. Please try again.');
        }
    }
    
    animateProgress() {
        const progressFill = document.getElementById('progressFill');
        const statusElement = document.getElementById('processingStatus');
        
        const steps = [
            { progress: 20, text: 'Uploading image...' },
            { progress: 40, text: 'Analyzing with AI...' },
            { progress: 70, text: 'Detecting subject...' },
            { progress: 90, text: 'Removing background...' },
            { progress: 100, text: 'Finalizing result...' }
        ];
        
        let currentStep = 0;
        
        const updateProgress = () => {
            if (currentStep < steps.length) {
                const step = steps[currentStep];
                progressFill.style.width = `${step.progress}%`;
                statusElement.textContent = step.text;
                currentStep++;
                setTimeout(updateProgress, 800);
            }
        };
        
        updateProgress();
    }
    
    async loadResults(data) {
        try {
            // Load preview
            const previewResponse = await fetch(`${this.apiBase}/preview/${this.currentFileId}`);
            const previewData = await previewResponse.json();
            
            if (previewData.success) {
                // Set result image
                const resultImage = document.getElementById('resultImage');
                resultImage.src = previewData.preview;
                
                // Set original image (from the file input)
                const fileInput = document.getElementById('fileInput');
                if (fileInput.files.length > 0) {
                    const originalImage = document.getElementById('originalImage');
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        originalImage.src = e.target.result;
                    };
                    reader.readAsDataURL(fileInput.files[0]);
                }
                
                // Update stats
                document.getElementById('processingTime').textContent = `${data.processing_time}s`;
                document.getElementById('modelUsed').textContent = this.getModelDisplayName(data.model_used);
                
                // Show results section
                this.showSection('resultsSection');
                
                // Reset editing state
                this.resetEditingState();
            }
            
        } catch (error) {
            console.error('Failed to load results:', error);
            this.showError('Failed to load results. Please try again.');
        }
    }
    
    getModelDisplayName(modelKey) {
        const modelNames = {
            'general': 'General Purpose',
            'human': 'Human Focused',
            'object': 'Object Detection',
            'advanced': 'Advanced'
        };
        return modelNames[modelKey] || modelKey;
    }
    
    // Editing methods
    selectTool(tool) {
        this.currentTool = tool;
        
        // Update tool button states
        document.querySelectorAll('.tool-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        const toolBtn = document.querySelector(`[data-tool="${tool}"]`);
        if (toolBtn) {
            toolBtn.classList.add('active');
        }
        
        // Update cursor
        const resultContainer = document.querySelector('.result-container');
        if (resultContainer) {
            resultContainer.classList.add('editing');
        }
    }
    
    startEditing(e) {
        if (!this.currentTool) return;
        
        this.isEditing = true;
        this.addEdit(e);
    }
    
    continueEditing(e) {
        if (!this.isEditing || !this.currentTool) return;
        
        this.addEdit(e);
    }
    
    stopEditing() {
        this.isEditing = false;
    }
    
    addEdit(e) {
        const rect = e.target.getBoundingClientRect();
        const x = Math.round((e.clientX - rect.left) * (e.target.naturalWidth / rect.width));
        const y = Math.round((e.clientY - rect.top) * (e.target.naturalHeight / rect.height));
        
        // Find existing edit of same type or create new one
        let currentEdit = this.edits.find(edit => 
            edit.type === this.currentTool && 
            edit.coordinates.length < 100 // Limit coordinates per edit
        );
        
        if (!currentEdit) {
            currentEdit = {
                type: this.currentTool,
                coordinates: []
            };
            this.edits.push(currentEdit);
        }
        
        currentEdit.coordinates.push({
            x: x,
            y: y,
            radius: this.brushSize
        });
        
        // Visual feedback (could add canvas overlay here)
        this.showEditFeedback(e.clientX, e.clientY);
    }
    
    showEditFeedback(x, y) {
        // Create a temporary visual indicator
        const indicator = document.createElement('div');
        indicator.style.position = 'fixed';
        indicator.style.left = `${x - this.brushSize/2}px`;
        indicator.style.top = `${y - this.brushSize/2}px`;
        indicator.style.width = `${this.brushSize}px`;
        indicator.style.height = `${this.brushSize}px`;
        indicator.style.borderRadius = '50%';
        indicator.style.border = '2px solid #667eea';
        indicator.style.pointerEvents = 'none';
        indicator.style.zIndex = '9999';
        indicator.style.opacity = '0.7';
        
        document.body.appendChild(indicator);
        
        setTimeout(() => {
            document.body.removeChild(indicator);
        }, 200);
    }
    
    async applyEdits() {
        if (this.edits.length === 0) {
            this.showMessage('No edits to apply.');
            return;
        }
        
        try {
            const response = await fetch(`${this.apiBase}/edit-mask`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    file_id: this.currentFileId,
                    edits: this.edits
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Reload the result
                await this.reloadResult();
                this.showMessage('Edits applied successfully!');
                this.resetEditingState();
            } else {
                throw new Error(data.error || 'Failed to apply edits');
            }
            
        } catch (error) {
            console.error('Edit application error:', error);
            this.showError('Failed to apply edits. Please try again.');
        }
    }
    
    async reloadResult() {
        try {
            const response = await fetch(`${this.apiBase}/preview/${this.currentFileId}`);
            const data = await response.json();
            
            if (data.success) {
                const resultImage = document.getElementById('resultImage');
                resultImage.src = data.preview + '?t=' + Date.now(); // Cache busting
            }
        } catch (error) {
            console.error('Failed to reload result:', error);
        }
    }
    
    resetEdits() {
        this.edits = [];
        this.resetEditingState();
        this.showMessage('Edits reset.');
    }
    
    resetEditingState() {
        this.currentTool = null;
        this.isEditing = false;
        this.edits = [];
        
        // Reset tool buttons
        document.querySelectorAll('.tool-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        // Reset cursor
        const resultContainer = document.querySelector('.result-container');
        if (resultContainer) {
            resultContainer.classList.remove('editing');
        }
    }
    
    // Download and actions
    async downloadResult() {
        if (!this.currentFileId) return;
        
        try {
            const response = await fetch(`${this.apiBase}/download/${this.currentFileId}`);
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `background_removed_${this.currentFileId}.png`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                
                this.showMessage('Download started!');
            } else {
                throw new Error('Download failed');
            }
            
        } catch (error) {
            console.error('Download error:', error);
            this.showError('Failed to download image. Please try again.');
        }
    }
    
    processAnother() {
        // Reset everything
        this.currentFileId = null;
        this.resetEditingState();
        
        // Clear file input
        const fileInput = document.getElementById('fileInput');
        if (fileInput) {
            fileInput.value = '';
        }
        
        // Reset progress
        const progressFill = document.getElementById('progressFill');
        if (progressFill) {
            progressFill.style.width = '0%';
        }
        
        // Show upload section
        this.showSection('uploadSection');
    }
    
    // UI management
    showSection(sectionId) {
        // Hide all sections
        const sections = ['uploadSection', 'processingSection', 'resultsSection', 'errorSection'];
        sections.forEach(id => {
            const section = document.getElementById(id);
            if (section) {
                section.style.display = 'none';
            }
        });
        
        // Show target section
        const targetSection = document.getElementById(sectionId);
        if (targetSection) {
            targetSection.style.display = 'block';
        }
    }
    
    showError(message) {
        const errorMessage = document.getElementById('errorMessage');
        if (errorMessage) {
            errorMessage.textContent = message;
        }
        this.showSection('errorSection');
    }
    
    showMessage(message) {
        // Simple toast notification (you could make this fancier)
        const toast = document.createElement('div');
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #667eea;
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 10000;
            font-weight: 600;
            transform: translateX(400px);
            transition: transform 0.3s ease;
        `;
        
        document.body.appendChild(toast);
        
        // Animate in
        setTimeout(() => {
            toast.style.transform = 'translateX(0)';
        }, 100);
        
        // Remove after delay
        setTimeout(() => {
            toast.style.transform = 'translateX(400px)';
            setTimeout(() => {
                document.body.removeChild(toast);
            }, 300);
        }, 3000);
    }
    
    showSuccessMessage() {
        const resultsCard = document.querySelector('.results-card');
        if (resultsCard) {
            resultsCard.classList.add('success-animation');
            setTimeout(() => {
                resultsCard.classList.remove('success-animation');
            }, 1000);
        }
    }
}

// Initialize the tool when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new BackgroundRemovalTool();
});

// Add some utility functions for mobile support
if ('ontouchstart' in window) {
    // Add touch support for editing on mobile devices
    document.addEventListener('touchstart', function(e) {
        if (e.target.id === 'resultImage') {
            e.preventDefault();
            const touch = e.touches[0];
            const mouseEvent = new MouseEvent('mousedown', {
                clientX: touch.clientX,
                clientY: touch.clientY
            });
            e.target.dispatchEvent(mouseEvent);
        }
    });
    
    document.addEventListener('touchmove', function(e) {
        if (e.target.id === 'resultImage') {
            e.preventDefault();
            const touch = e.touches[0];
            const mouseEvent = new MouseEvent('mousemove', {
                clientX: touch.clientX,
                clientY: touch.clientY
            });
            e.target.dispatchEvent(mouseEvent);
        }
    });
    
    document.addEventListener('touchend', function(e) {
        if (e.target.id === 'resultImage') {
            e.preventDefault();
            const mouseEvent = new MouseEvent('mouseup', {});
            e.target.dispatchEvent(mouseEvent);
        }
    });
}