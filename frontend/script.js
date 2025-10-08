const API_BASE_URL = "https://acadrive.onrender.com";

const uploadForm = document.getElementById("uploadForm");
const searchForm = document.getElementById("searchForm");
const uploadStatus = document.getElementById("uploadStatus");
const resultsDiv = document.getElementById("results");

// Replace your old uploadForm event listener with this new one
uploadForm.addEventListener("submit", (e) => {
    e.preventDefault();

    const subject = document.getElementById("subject").value;
    const file = document.getElementById("file").files[0];
    const uploadStatus = document.getElementById("uploadStatus");
    const progressBarContainer = document.getElementById("progressBarContainer");
    const progressBar = document.getElementById("progressBar");

    if (!file) {
        uploadStatus.textContent = "Please select a file.";
        return;
    }

    const formData = new FormData();
    formData.append("subject", subject);
    formData.append("file", file);

    // --- Logic for the progress bar ---
    const xhr = new XMLHttpRequest();

    // Listen for progress events
    xhr.upload.addEventListener("progress", (e) => {
        if (e.lengthComputable) {
            const percentComplete = Math.round((e.loaded / e.total) * 100);
            progressBar.style.width = percentComplete + '%';
            progressBar.textContent = percentComplete + '%';
        }
    });

    // Handle successful upload
    xhr.onload = () => {
        if (xhr.status === 200) {
            const result = JSON.parse(xhr.responseText);
            uploadStatus.textContent = `Success! File "${result.filename}" uploaded.`;
            uploadForm.reset();
        } else {
            uploadStatus.textContent = `Upload failed. Server responded with status: ${xhr.status}`;
        }
        // Hide progress bar after a short delay
        setTimeout(() => { progressBarContainer.style.display = 'none'; }, 2000);
    };

    // Handle upload errors
    xhr.onerror = () => {
        uploadStatus.textContent = "Upload failed. An error occurred.";
        progressBar.style.backgroundColor = 'var(--error-color)';
        setTimeout(() => { progressBarContainer.style.display = 'none'; }, 2000);
    };

    // --- Start the upload ---
    xhr.open("POST", `${API_BASE_URL}/upload/`);
    
    // Reset status and show the progress bar before sending
    uploadStatus.textContent = "";
    progressBar.style.width = '0%';
    progressBar.textContent = '0%';
    progressBar.style.backgroundColor = 'var(--success-color)';
    progressBarContainer.style.display = 'block';

    xhr.send(formData);
});
// New code for real-time search
const searchQuery = document.getElementById("searchQuery");
let debounceTimer;

searchQuery.addEventListener('input', (e) => {
    // This is a "debounce" function. It waits for the user to stop typing
    // for 300ms before sending a request to the server. This is efficient
    // and prevents sending too many requests.
    clearTimeout(debounceTimer);
    
    debounceTimer = setTimeout(() => {
        const query = e.target.value;
        
        // Only search if the query isn't empty
        if (query.length > 0) {
            resultsDiv.innerHTML = "Searching...";
            fetchResults(query);
        } else {
            resultsDiv.innerHTML = ""; // Clear results if search bar is empty
        }
    }, 300);
});

async function fetchResults(query) {
    try {
        const response = await fetch(`${API_BASE_URL}/search/?query=${encodeURIComponent(query)}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const files = await response.json();
        displayResults(files);
    } catch (error) {
        resultsDiv.innerHTML = `<p>Error searching: ${error.message}</p>`;
    }
}

function displayResults(files) {
    if (files.length === 0) {
        resultsDiv.innerHTML = "<p>No files found.</p>";
        return;
    }
    resultsDiv.innerHTML = files.map(file => {
        const isPdf = file.filename.toLowerCase().endsWith('.pdf');
        // If it's a PDF, link to our preview page. Otherwise, link directly to the file.
        const linkTarget = isPdf 
            ? `./preview.html?file=${encodeURIComponent(file.file_url)}`
            : file.file_url;

        return `
            <div class="file-item" id="file-item-${file.id}">
                <div class="file-info">
                    <a href="${linkTarget}" target="_blank" rel="noopener noreferrer">${file.filename}</a>
                    <p><strong>Subject:</strong> ${file.subject}</p>
                    <p><strong>Size:</strong> ${formatFileSize(file.file_size)}</p>
                </div>
                <button class="delete-btn" data-id="${file.id}">Delete</button>
            </div>
        `;
    }).join("");
}


function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}
// Add these new functions and the event listener to script.js

// This function will run when the webpage first loads
document.addEventListener('DOMContentLoaded', () => {
    fetchRecentFiles();
});

// This function gets the recent files data from the backend
async function fetchRecentFiles() {
    const container = document.getElementById('recent-files-container');
    container.innerHTML = "Loading recent files...";
    try {
        const response = await fetch(`${API_BASE_URL}/files/recent`);
        if (!response.ok) {
            throw new Error('Could not fetch recent files.');
        }
        const files = await response.json();
        displayRecentFiles(files);
    } catch (error) {
        container.innerHTML = `<p>${error.message}</p>`;
    }
}

// This function creates the HTML for the preview cards
function displayRecentFiles(files) {
    const container = document.getElementById('recent-files-container');
    if (files.length === 0) {
        container.innerHTML = "<p>No recent uploads yet.</p>";
        return;
    }
    container.innerHTML = files.map(file => {
        const previewContent = file.preview_url
            ? `<img src="${file.preview_url}" alt="${file.filename}">`
            : `<div class="file-icon">📄</div>`;

        const isPdf = file.filename.toLowerCase().endsWith('.pdf');
        // If it's a PDF, link to our preview page. Otherwise, link directly to the file.
        const linkTarget = isPdf
            ? `./preview.html?file=${encodeURIComponent(file.file_url)}`
            : file.file_url;

        return `
            <div class="recent-file-card">
                <a href="${linkTarget}" target="_blank" rel="noopener noreferrer">
                    <div class="preview">
                        ${previewContent}
                    </div>
                    <div class="filename">${file.filename}</div>
                </a>
            </div>
        `;
    }).join('');
}