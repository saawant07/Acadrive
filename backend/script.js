// Configuration - Point to your local server
const API_BASE_URL = "http://localhost:8000";

// State management
let appState = {
    recentFiles: [],
    searchResults: [],
    stats: {
        total_files: 0,
        total_subjects: 0,
        active_users: 0
    }
};

// DOM Elements
const elements = {
    uploadForm: document.getElementById("uploadForm"),
    uploadStatus: document.getElementById("uploadStatus"),
    resultsDiv: document.getElementById("results"),
    searchQuery: document.getElementById("searchQuery"),
    recentFilesContainer: document.getElementById('recent-files-container'),
    clearSearch: document.getElementById('clearSearch'),
    refreshRecent: document.getElementById('refresh-recent'),
    progressBarContainer: document.getElementById("progressBarContainer"),
    progressBar: document.getElementById("progressBar"),
    progressPercent: document.getElementById("progressPercent"),
    fileName: document.getElementById("fileName"),
    fileInput: document.getElementById("file"),
    totalFiles: document.getElementById("total-files"),
    totalSubjects: document.getElementById("total-subjects"),
    activeUsers: document.getElementById("active-users"),
    toast: document.getElementById("toast")
};

// Initialize application
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

async function initializeApp() {
    setupEventListeners();
    await Promise.all([
        fetchRecentFiles(),
        fetchStats()
    ]);
    showToast('Welcome to Acadrive! Your academic file hub is ready.', 'success');
}

function setupEventListeners() {
    elements.uploadForm.addEventListener("submit", handleFileUpload);
    elements.fileInput.addEventListener("change", handleFileInputChange);
    elements.searchQuery.addEventListener('input', handleSearchInput);
    elements.clearSearch.addEventListener('click', clearSearch);
    elements.refreshRecent.addEventListener('click', handleRefreshRecent);
}

async function handleFileUpload(e) {
    e.preventDefault();
    
    const subject = document.getElementById("subject").value.trim();
    const file = elements.fileInput.files[0];
    
    if (!subject) {
        showStatus('Please enter a subject or course code.', 'error');
        return;
    }
    
    if (!file) {
        showStatus('Please select a file.', 'error');
        return;
    }

    const formData = new FormData();
    formData.append("subject", subject);
    formData.append("file", file);

    await uploadFileWithProgress(formData);
}

async function uploadFileWithProgress(formData) {
    showProgressBar();
    showStatus('Uploading file...', 'info');
    disableForm(true);

    try {
        const response = await fetch(`${API_BASE_URL}/upload/`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Upload failed');
        }

        const result = await response.json();
        handleUploadSuccess(result);
    } catch (error) {
        handleUploadError(error);
    } finally {
        setTimeout(hideProgressBar, 1000);
        disableForm(false);
    }
}

function handleUploadSuccess(response) {
    showStatus('File uploaded successfully!', 'success');
    elements.uploadForm.reset();
    elements.fileName.textContent = 'No file chosen';
    showToast('File uploaded successfully!', 'success');
    
    // Refresh data
    Promise.all([
        fetchRecentFiles(),
        fetchStats()
    ]);
}

function handleUploadError(error) {
    console.error('Upload error:', error);
    showStatus(`Upload failed: ${error.message}`, 'error');
    showToast('Upload failed. Please try again.', 'error');
}

// Progress bar functions
function showProgressBar() {
    elements.progressBarContainer.style.display = 'block';
    updateProgressBar(0);
}

function hideProgressBar() {
    elements.progressBarContainer.style.display = 'none';
}

function updateProgressBar(percent) {
    elements.progressBar.style.width = `${percent}%`;
    elements.progressPercent.textContent = `${percent}%`;
}

function disableForm(disabled) {
    const submitBtn = elements.uploadForm.querySelector('button[type="submit"]');
    const inputs = elements.uploadForm.querySelectorAll('input, button');
    
    inputs.forEach(input => {
        input.disabled = disabled;
    });
    
    if (disabled) {
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading...';
    } else {
        submitBtn.innerHTML = '<i class="fas fa-upload"></i> Upload File';
    }
}

// API functions
async function fetchRecentFiles() {
    try {
        const response = await fetch(`${API_BASE_URL}/files/recent`);
        if (!response.ok) throw new Error('Could not fetch recent files.');
        
        const files = await response.json();
        appState.recentFiles = files;
        displayRecentFiles(files);
    } catch (error) {
        console.error('Error fetching recent files:', error);
    }
}

async function fetchStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/stats`);
        if (!response.ok) throw new Error('Could not fetch stats.');
        
        const stats = await response.json();
        appState.stats = stats;
        updateStatsDisplay(stats);
    } catch (error) {
        console.error('Error fetching stats:', error);
    }
}

// Display functions
function displayRecentFiles(files) {
    if (!files || files.length === 0) {
        elements.recentFilesContainer.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-folder-open"></i>
                <p>No recent files found</p>
                <small>Upload your first file to get started</small>
            </div>
        `;
        return;
    }

    const filesHTML = files.map(file => createFileCard(file)).join('');
    elements.recentFilesContainer.innerHTML = filesHTML;
}

function createFileCard(file) {
    const fileExtension = file.filename.split('.').pop().toLowerCase();
    const fileIcon = getFileIcon(fileExtension);
    
    return `
        <div class="recent-file-card">
            <div class="file-header">
                <div class="file-icon">
                    <i class="${fileIcon}"></i>
                </div>
                <div class="file-info">
                    <a href="${file.file_url}" target="_blank" class="course-name">
                        ${file.subject}
                    </a>
                    <div class="file-details">
                        <span class="file-original-name">${file.filename}</span>
                        <span class="file-size">${formatFileSize(file.file_size)}</span>
                    </div>
                </div>
            </div>
            <a href="${file.file_url}" download="${file.filename}" class="card-download-btn">
                <i class="fas fa-download"></i> Download
            </a>
        </div>
    `;
}

function getFileIcon(extension) {
    const iconMap = {
        'pdf': 'fas fa-file-pdf',
        'doc': 'fas fa-file-word',
        'docx': 'fas fa-file-word',
        'jpg': 'fas fa-file-image',
        'jpeg': 'fas fa-file-image',
        'png': 'fas fa-file-image',
        'ppt': 'fas fa-file-powerpoint',
        'pptx': 'fas fa-file-powerpoint',
        'txt': 'fas fa-file-alt',
        'default': 'fas fa-file'
    };
    return iconMap[extension] || iconMap.default;
}

function formatFileSize(bytes) {
    if (!bytes || bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function updateStatsDisplay(stats) {
    elements.totalFiles.textContent = stats.total_files;
    elements.totalSubjects.textContent = stats.total_subjects;
    elements.activeUsers.textContent = stats.active_users;
}

// Utility functions
function showStatus(message, type) {
    elements.uploadStatus.textContent = message;
    elements.uploadStatus.className = `status-message ${type}`;
    elements.uploadStatus.style.display = 'block';
    
    if (type === 'success' || type === 'error') {
        setTimeout(() => {
            elements.uploadStatus.style.display = 'none';
        }, 5000);
    }
}

function showToast(message, type) {
    const icon = type === 'success' ? 'fas fa-check-circle' : 'fas fa-exclamation-triangle';
    
    elements.toast.innerHTML = `
        <div class="toast-content">
            <i class="${icon}"></i>
            <span>${message}</span>
        </div>
    `;
    
    elements.toast.className = `toast ${type} show`;
    
    setTimeout(() => {
        elements.toast.classList.remove('show');
    }, 4000);
}

function handleFileInputChange(e) {
    const file = e.target.files[0];
    if (file) {
        elements.fileName.textContent = file.name;
        elements.fileName.style.color = 'var(--text-primary)';
    } else {
        elements.fileName.textContent = 'No file chosen';
        elements.fileName.style.color = 'var(--text-muted)';
    }
}

function handleSearchInput(e) {
    const query = e.target.value.trim();
    if (query.length >= 2) {
        fetch(`${API_BASE_URL}/search/?query=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(results => {
                // Handle search results
                console.log('Search results:', results);
            });
    }
}

function clearSearch() {
    elements.searchQuery.value = '';
}

function handleRefreshRecent() {
    fetchRecentFiles();
    showToast('Recent files updated', 'success');
}
