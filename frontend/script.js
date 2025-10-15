// Configuration - Dynamic API URL based on environment
const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
    ? "http://localhost:8000" 
    : "https://acadrive-backend-production.up.railway.app";

console.log('API Base URL:', API_BASE_URL);

// State management
let appState = {
    recentFiles: [],
    searchResults: [],
    stats: {
        total_files: 0,
        total_subjects: 0,
        active_users: 0
    },
    filters: {
        subject: '',
        type: ''
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
    toast: document.getElementById("toast"),
    filterSubject: document.getElementById("filterSubject"),
    filterType: document.getElementById("filterType")
};

let debounceTimer;

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
    if (elements.uploadForm) {
        elements.uploadForm.addEventListener("submit", handleFileUpload);
    }
    if (elements.fileInput) {
        elements.fileInput.addEventListener("change", handleFileInputChange);
        setupDragAndDrop();
    }
    if (elements.searchQuery) {
        elements.searchQuery.addEventListener('input', handleSearchInput);
    }
    if (elements.clearSearch) {
        elements.clearSearch.addEventListener('click', clearSearch);
    }
    if (elements.refreshRecent) {
        elements.refreshRecent.addEventListener('click', handleRefreshRecent);
    }
    if (elements.filterSubject && elements.filterType) {
        elements.filterSubject.addEventListener('change', handleFilterChange);
        elements.filterType.addEventListener('change', handleFilterChange);
    }
}

function handleFileInputChange(e) {
    const file = e.target.files[0];
    const fileNameDisplay = document.getElementById("fileName");

    if (file) {
        fileNameDisplay.textContent = file.name;
        fileNameDisplay.style.color = 'var(--text-primary)';
    } else {
        fileNameDisplay.textContent = 'No file chosen';
        fileNameDisplay.style.color = 'var(--text-muted)';
    }
}

function setupDragAndDrop() {
    const fileInputLabel = document.querySelector('.file-input-label');
    if (!fileInputLabel) return;
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        fileInputLabel.addEventListener(eventName, e => {
            e.preventDefault();
            e.stopPropagation();
        }, false);
    });
    
    ['dragenter', 'dragover'].forEach(eventName => {
        fileInputLabel.addEventListener(eventName, () => {
            fileInputLabel.style.borderColor = 'var(--primary)';
        }, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        fileInputLabel.addEventListener(eventName, () => {
            fileInputLabel.style.borderColor = 'var(--border)';
        }, false);
    });
    
    fileInputLabel.addEventListener('drop', e => {
        const dt = e.dataTransfer;
        const files = dt.files;
        elements.fileInput.files = files;
        handleFileInputChange({ target: elements.fileInput });
    }, false);
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

    // Validate file size (50MB)
    if (file.size > 50 * 1024 * 1024) {
        showStatus('File size exceeds 50MB limit.', 'error');
        return;
    }

    const formData = new FormData();
    formData.append("subject", subject);
    formData.append("file", file);

    await uploadFileWithProgress(formData);
}

function handleFilterChange() {
    appState.filters.subject = elements.filterSubject.value;
    appState.filters.type = elements.filterType.value;
    
    const currentQuery = elements.searchQuery.value.trim();
    if (currentQuery.length >= 2) {
        fetchResults(currentQuery);
    }
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
        showStatus('File uploaded successfully!', 'success');
        elements.uploadForm.reset();
        handleFileInputChange({ target: elements.fileInput });
        showToast('File uploaded successfully!', 'success');
        
        // Refresh data
        await Promise.all([fetchRecentFiles(), fetchStats()]);
        
    } catch (error) {
        console.error('Upload error:', error);
        showStatus(`Upload failed: ${error.message}`, 'error');
        showToast('Upload failed. Please try again.', 'error');
    } finally {
        setTimeout(hideProgressBar, 1000);
        disableForm(false);
    }
}

function disableForm(disabled) {
    const submitBtn = elements.uploadForm.querySelector('button[type="submit"]');
    const inputs = elements.uploadForm.querySelectorAll('input, button, select');
    
    inputs.forEach(input => {
        input.disabled = disabled;
    });
    
    if (disabled) {
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading...';
    } else {
        submitBtn.innerHTML = '<i class="fas fa-upload"></i> Upload File';
    }
}

function showProgressBar() {
    if (elements.progressBarContainer) {
        elements.progressBarContainer.style.display = 'block';
        updateProgressBar(0);
    }
}

function hideProgressBar() {
    if (elements.progressBarContainer) {
        elements.progressBarContainer.style.display = 'none';
    }
}

function updateProgressBar(percent) {
    if (elements.progressBar && elements.progressPercent) {
        elements.progressBar.style.width = `${percent}%`;
        elements.progressPercent.textContent = `${percent}%`;
    }
}

function handleSearchInput(e) {
    clearTimeout(debounceTimer);
    const query = e.target.value.trim();
    
    if (elements.clearSearch) {
        elements.clearSearch.style.display = query ? 'block' : 'none';
    }
    
    debounceTimer = setTimeout(() => {
        if (query.length >= 2) {
            fetchResults(query);
        } else if (query.length === 0) {
            clearSearch();
        }
    }, 300);
}

function clearSearch() {
    if (elements.searchQuery) {
        elements.searchQuery.value = '';
    }
    if (elements.clearSearch) {
        elements.clearSearch.style.display = 'none';
    }
    showEmptySearchState();
}

function showEmptySearchState() {
    if (elements.resultsDiv) {
        elements.resultsDiv.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-search"></i>
                <p>Enter a search term to find files</p>
            </div>
        `;
    }
}

async function handleRefreshRecent() {
    const btn = elements.refreshRecent;
    if (!btn) return;
    
    const originalHtml = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    btn.disabled = true;
    
    await fetchRecentFiles();
    
    setTimeout(() => {
        btn.innerHTML = originalHtml;
        btn.disabled = false;
        showToast('Recent files updated', 'success');
    }, 500);
}

async function fetchRecentFiles() {
    if (!elements.recentFilesContainer) return;
    
    showLoading(elements.recentFilesContainer);
    
    try {
        const response = await fetch(`${API_BASE_URL}/files/recent`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const files = await response.json();
        appState.recentFiles = files;
        displayRecentFiles(files);
    } catch (error) {
        console.error('Error fetching recent files:', error);
        showError(elements.recentFilesContainer, 'Failed to load recent files. Please try again.');
    }
}

async function fetchResults(query) {
    if (!elements.resultsDiv) return;
    
    showLoading(elements.resultsDiv);
    
    try {
        let url = `${API_BASE_URL}/search/?query=${encodeURIComponent(query)}`;
        
        const params = new URLSearchParams();
        if (appState.filters.subject) {
            params.append('subject', appState.filters.subject);
        }
        if (appState.filters.type) {
            params.append('file_type', appState.filters.type);
        }
        
        const filterString = params.toString();
        if (filterString) {
            url += `&${filterString}`;
        }
        
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const results = await response.json();
        appState.searchResults = results;
        displaySearchResults(results);
    } catch (error) {
        console.error('Error fetching search results:', error);
        showError(elements.resultsDiv, 'Search failed. Please try again.');
    }
}

async function fetchStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/stats`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const stats = await response.json();
        appState.stats = stats;
        updateStatsDisplay(stats);
    } catch (error) {
        console.error('Error fetching stats:', error);
    }
}

function displayRecentFiles(files) {
    if (!elements.recentFilesContainer) return;
    
    if (!files || files.length === 0) {
        elements.recentFilesContainer.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-folder-open"></i>
                <p>No recent files yet</p>
                <small>Upload your first file to get started</small>
            </div>
        `;
        return;
    }
    
    elements.recentFilesContainer.innerHTML = files.map(createFileCard).join('');
}

function displaySearchResults(results) {
    if (!elements.resultsDiv) return;
    
    if (!results || results.length === 0) {
        elements.resultsDiv.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-search"></i>
                <p>No files found</p>
                <small>Try different search terms or filters</small>
            </div>
        `;
        return;
    }
    
    elements.resultsDiv.innerHTML = results.map(createFileItem).join('');
}

function createFileCard(file) {
    const isPdf = getFileExtension(file.filename) === 'pdf';
    const linkTarget = isPdf ? `./preview.html?file=${encodeURIComponent(file.file_url)}` : file.file_url;
    
    return `
        <div class="recent-file-card">
            <div class="file-header">
                <div class="file-icon">
                    <i class="${getFileIcon(getFileExtension(file.filename))}"></i>
                </div>
                <div class="file-info">
                    <a href="${linkTarget}" target="_blank" class="course-name">${escapeHtml(file.subject)}</a>
                    <div class="file-details">
                        <span class="file-original-name">${escapeHtml(file.filename)}</span>
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

function createFileItem(file) {
    return `
        <div class="file-item">
            <div class="file-info">
                <a href="${file.file_url}" target="_blank">
                    <i class="${getFileIcon(getFileExtension(file.filename))}"></i> 
                    ${escapeHtml(file.filename)}
                </a>
                <div class="file-details">
                    <span class="file-detail">
                        <i class="fas fa-book"></i> ${escapeHtml(file.subject)}
                    </span>
                    <span class="file-detail">
                        <i class="fas fa-weight-hanging"></i> ${formatFileSize(file.file_size)}
                    </span>
                    <span class="file-detail">
                        <i class="fas fa-calendar"></i> ${formatDate(file.created_at)}
                    </span>
                </div>
            </div>
            <a href="${file.file_url}" download="${file.filename}" class="download-btn">
                <i class="fas fa-download"></i> Download
            </a>
        </div>
    `;
}

// Utility functions
function getFileExtension(filename) {
    return filename.split('.').pop().toLowerCase();
}

function getFileIcon(ext) {
    const iconMap = {
        'pdf': 'fas fa-file-pdf',
        'doc': 'fas fa-file-word',
        'docx': 'fas fa-file-word',
        'jpg': 'fas fa-file-image',
        'jpeg': 'fas fa-file-image', 
        'png': 'fas fa-file-image',
        'ppt': 'fas fa-file-powerpoint',
        'pptx': 'fas fa-file-powerpoint',
        'txt': 'fas fa-file-alt'
    };
    return iconMap[ext] || 'fas fa-file';
}

function formatFileSize(bytes) {
    if (!bytes || bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDate(dateString) {
    if (!dateString) return 'Unknown';
    try {
        return new Date(dateString).toLocaleDateString();
    } catch {
        return 'Unknown';
    }
}

function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function showLoading(container) {
    if (container) {
        container.innerHTML = `
            <div class="loading-placeholder">
                <i class="fas fa-spinner fa-spin"></i>
                <p>Loading...</p>
            </div>
        `;
    }
}

function showError(container, message) {
    if (container) {
        container.innerHTML = `
            <div class="empty-state error">
                <i class="fas fa-exclamation-triangle"></i>
                <p>${message}</p>
            </div>
        `;
    }
}

function showStatus(message, type) {
    if (elements.uploadStatus) {
        elements.uploadStatus.textContent = message;
        elements.uploadStatus.className = `status-message ${type}`;
        elements.uploadStatus.style.display = 'block';
        
        setTimeout(() => {
            if (elements.uploadStatus) {
                elements.uploadStatus.style.display = 'none';
            }
        }, 5000);
    }
}

function updateStatsDisplay(stats) {
    if (elements.totalFiles) elements.totalFiles.textContent = stats.total_files;
    if (elements.totalSubjects) elements.totalSubjects.textContent = stats.total_subjects;
    if (elements.activeUsers) elements.activeUsers.textContent = stats.active_users;
}

function showToast(message, type) {
    if (!elements.toast) return;
    
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