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

// Background Removal Tool
let selectedFile = null;
let currentResultId = null;
const API_BASE_URL = 'http://localhost:5000/api';

// Initialize background removal tool
document.addEventListener('DOMContentLoaded', function() {
  initializeBackgroundRemovalTool();
});

function initializeBackgroundRemovalTool() {
  const uploadArea = document.getElementById('uploadArea');
  const imageInput = document.getElementById('imageInput');
  const featherRadius = document.getElementById('featherRadius');
  const featherValue = document.getElementById('featherValue');
  
  // File input change handler
  imageInput.addEventListener('change', handleFileSelect);
  
  // Upload area click handler
  uploadArea.addEventListener('click', () => imageInput.click());
  
  // Drag and drop handlers
  uploadArea.addEventListener('dragover', handleDragOver);
  uploadArea.addEventListener('dragleave', handleDragLeave);
  uploadArea.addEventListener('drop', handleDrop);
  
  // Feather radius slider
  featherRadius.addEventListener('input', function() {
    featherValue.textContent = this.value;
  });
  
  // Prevent default drag behaviors on the document
  document.addEventListener('dragover', e => e.preventDefault());
  document.addEventListener('drop', e => e.preventDefault());
}

function handleFileSelect(event) {
  const file = event.target.files[0];
  if (file) {
    processFileSelection(file);
  }
}

function handleDragOver(event) {
  event.preventDefault();
  event.currentTarget.classList.add('dragover');
}

function handleDragLeave(event) {
  event.currentTarget.classList.remove('dragover');
}

function handleDrop(event) {
  event.preventDefault();
  event.currentTarget.classList.remove('dragover');
  
  const files = event.dataTransfer.files;
  if (files.length > 0) {
    processFileSelection(files[0]);
  }
}

function processFileSelection(file) {
  // Validate file type
  const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp', 'image/bmp', 'image/tiff'];
  if (!allowedTypes.includes(file.type)) {
    showError('نوع الملف غير مدعوم. يرجى اختيار صورة PNG, JPG, أو WEBP');
    return;
  }
  
  // Validate file size (16MB max)
  const maxSize = 16 * 1024 * 1024;
  if (file.size > maxSize) {
    showError('حجم الملف كبير جداً. الحد الأقصى 16MB');
    return;
  }
  
  selectedFile = file;
  
  // Show file info and options
  const uploadArea = document.getElementById('uploadArea');
  uploadArea.innerHTML = `
    <div class="upload-content">
      <div class="upload-icon">✅</div>
      <p><strong>${file.name}</strong></p>
      <p class="upload-hint">${formatFileSize(file.size)} - ${file.type.split('/')[1].toUpperCase()}</p>
    </div>
  `;
  
  // Show processing options
  document.getElementById('processingOptions').style.display = 'block';
  
  // Preview original image
  previewOriginalImage(file);
}

function formatFileSize(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function previewOriginalImage(file) {
  const reader = new FileReader();
  reader.onload = function(e) {
    const img = new Image();
    img.onload = function() {
      const canvas = document.getElementById('originalCanvas');
      const ctx = canvas.getContext('2d');
      
      // Calculate display size (max 300px)
      const maxSize = 300;
      let { width, height } = calculateDisplaySize(img.width, img.height, maxSize);
      
      canvas.width = width;
      canvas.height = height;
      
      ctx.drawImage(img, 0, 0, width, height);
      
      // Show preview container
      document.getElementById('previewContainer').style.display = 'block';
    };
    img.src = e.target.result;
  };
  reader.readAsDataURL(file);
}

function calculateDisplaySize(originalWidth, originalHeight, maxSize) {
  let width = originalWidth;
  let height = originalHeight;
  
  if (width > height) {
    if (width > maxSize) {
      height = (height * maxSize) / width;
      width = maxSize;
    }
  } else {
    if (height > maxSize) {
      width = (width * maxSize) / height;
      height = maxSize;
    }
  }
  
  return { width, height };
}

async function processImage() {
  if (!selectedFile) {
    showError('يرجى اختيار صورة أولاً');
    return;
  }
  
  const processBtn = document.getElementById('processBtn');
  const progressContainer = document.getElementById('progressContainer');
  const progressFill = document.getElementById('progressFill');
  const progressText = document.getElementById('progressText');
  
  // Disable process button
  processBtn.disabled = true;
  processBtn.textContent = 'جاري المعالجة...';
  
  // Show progress
  progressContainer.style.display = 'block';
  progressFill.style.width = '0%';
  progressText.textContent = 'جاري رفع الصورة...';
  
  try {
    // Prepare form data
    const formData = new FormData();
    formData.append('image', selectedFile);
    formData.append('method', document.getElementById('methodSelect').value);
    formData.append('feather_radius', document.getElementById('featherRadius').value);
    formData.append('enhance_edges', document.getElementById('enhanceEdges').checked);
    
    // Simulate progress updates
    const progressInterval = setInterval(() => {
      const currentWidth = parseInt(progressFill.style.width) || 0;
      if (currentWidth < 90) {
        progressFill.style.width = (currentWidth + 5) + '%';
      }
    }, 200);
    
    progressText.textContent = 'جاري معالجة الصورة بالذكاء الاصطناعي...';
    
    // Send request to backend
    const response = await fetch(`${API_BASE_URL}/remove-background`, {
      method: 'POST',
      body: formData
    });
    
    clearInterval(progressInterval);
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'فشل في معالجة الصورة');
    }
    
    const result = await response.json();
    
    if (result.success) {
      currentResultId = result.result_id;
      
      // Complete progress
      progressFill.style.width = '100%';
      progressText.textContent = 'تم! جاري تحميل النتيجة...';
      
      // Load and display result
      await displayResult(result.download_url);
      
      // Hide progress and show result actions
      progressContainer.style.display = 'none';
      document.getElementById('resultActions').style.display = 'flex';
      
      showSuccess('تم إزالة الخلفية بنجاح!');
    } else {
      throw new Error('فشل في معالجة الصورة');
    }
    
  } catch (error) {
    console.error('Processing error:', error);
    showError(error.message || 'حدث خطأ أثناء معالجة الصورة');
    progressContainer.style.display = 'none';
  } finally {
    // Re-enable process button
    processBtn.disabled = false;
    processBtn.textContent = 'معالجة الصورة';
  }
}

async function displayResult(downloadUrl) {
  try {
    // Fetch the result image
    const response = await fetch(downloadUrl);
    const blob = await response.blob();
    
    // Create image URL
    const imageUrl = URL.createObjectURL(blob);
    
    // Display in canvas
    const img = new Image();
    img.onload = function() {
      const canvas = document.getElementById('resultCanvas');
      const ctx = canvas.getContext('2d');
      
      // Calculate display size
      const maxSize = 300;
      let { width, height } = calculateDisplaySize(img.width, img.height, maxSize);
      
      canvas.width = width;
      canvas.height = height;
      
      // Clear canvas with checkerboard pattern for transparency
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, width, height);
      
      // Draw the image
      ctx.drawImage(img, 0, 0, width, height);
      
      // Clean up
      URL.revokeObjectURL(imageUrl);
    };
    img.src = imageUrl;
    
  } catch (error) {
    console.error('Error displaying result:', error);
    showError('فشل في عرض النتيجة');
  }
}

async function downloadResult() {
  if (!currentResultId) {
    showError('لا توجد نتيجة للتحميل');
    return;
  }
  
  try {
    const downloadUrl = `${API_BASE_URL}/download/${currentResultId}`;
    
    // Create a temporary link and click it
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = `no_background_${Date.now()}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    showSuccess('تم بدء التحميل!');
    
  } catch (error) {
    console.error('Download error:', error);
    showError('فشل في تحميل الصورة');
  }
}

function resetTool() {
  // Reset all variables
  selectedFile = null;
  currentResultId = null;
  
  // Reset UI
  const uploadArea = document.getElementById('uploadArea');
  uploadArea.innerHTML = `
    <div class="upload-content">
      <div class="upload-icon">📁</div>
      <p>اضغط هنا أو اسحب الصورة</p>
      <p class="upload-hint">PNG, JPG, WEBP (حتى 16MB)</p>
    </div>
  `;
  
  // Hide sections
  document.getElementById('processingOptions').style.display = 'none';
  document.getElementById('previewContainer').style.display = 'none';
  document.getElementById('progressContainer').style.display = 'none';
  document.getElementById('resultActions').style.display = 'none';
  
  // Clear output
  document.getElementById('backgroundOutput').innerHTML = '';
  
  // Reset file input
  document.getElementById('imageInput').value = '';
  
  // Reset options to defaults
  document.getElementById('methodSelect').value = 'auto';
  document.getElementById('featherRadius').value = 2;
  document.getElementById('featherValue').textContent = '2';
  document.getElementById('enhanceEdges').checked = true;
}

function showError(message) {
  const output = document.getElementById('backgroundOutput');
  output.innerHTML = `<div style="color: #dc3545; font-weight: 500;">❌ ${message}</div>`;
  setTimeout(() => {
    output.innerHTML = '';
  }, 5000);
}

function showSuccess(message) {
  const output = document.getElementById('backgroundOutput');
  output.innerHTML = `<div style="color: #28a745; font-weight: 500;">✅ ${message}</div>`;
  setTimeout(() => {
    output.innerHTML = '';
  }, 3000);
}
