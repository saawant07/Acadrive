import os
import aiofiles
import aiosqlite
import sqlite3
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import re

# Setup
BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)
DB_PATH = BASE_DIR / "acadrive.db"

# FastAPI App Initialization
app = FastAPI(title="Acadrive API")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your frontend's domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def init_db():
    """Initializes the SQLite database and creates the files table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # This is a one-time sync operation, so standard sqlite3 is fine here.
    conn.execute('''CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            subject TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_url TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            file_type TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
    conn.commit()
    conn.close()

@app.on_event("startup")
async def startup_event():
    """Run on startup to initialize the database."""
    init_db()

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

def secure_filename(filename: str) -> str:
    """Sanitizes a filename to be safe for storage."""
    # Remove directory traversal attempts
    filename = filename.lstrip('./\\')
    # Keep only-safe characters
    return re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)

@app.post("/upload/")
async def upload_file(subject: str = Form(...), file: UploadFile = File(...)):
    """Handles file uploads, sanitizes filename, saves file, and records it in the database."""
    try:
        # Security: Limit file size (e.g., 50MB)
        contents = await file.read()
        file_size = len(contents)
        if file_size > 50 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large")
        
        # Create safe filename
        safe_filename = secure_filename(file.filename)
        file_path = UPLOADS_DIR / safe_filename
        
        # Handle potential filename collisions
        counter = 1
        final_filename = safe_filename
        while file_path.exists():
            name, ext = os.path.splitext(safe_filename)
            final_filename = f"{name}_{counter}{ext}"
            file_path = UPLOADS_DIR / final_filename
            counter += 1

        async with aiofiles.open(file_path, 'wb') as out_file:
            await out_file.write(contents)

        # Determine file type
        file_type = 'document'
        if final_filename.lower().endswith('.pdf'):
            file_type = 'pdf'
        elif final_filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            file_type = 'image'
        
        # Create database record
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                '''INSERT INTO files (filename, subject, file_path, file_url, file_size, file_type) VALUES (?, ?, ?, ?, ?, ?)''',
                (final_filename, subject, str(file_path), f"/uploads/{final_filename}", file_size, file_type)
            )
            await db.commit()
            file_id = cursor.lastrowid
        
        return {
            "id": file_id,
            "filename": final_filename,
            "subject": subject,
            "file_url": f"/uploads/{final_filename}",
            "file_size": file_size,
            "file_type": file_type
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")

@app.get("/files/recent")
async def get_recent_files():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT id, filename, subject, file_url, file_size, file_type, created_at 
            FROM files ORDER BY created_at DESC LIMIT 10
        ''')
        files = await cursor.fetchall()
    
    result = []
    for file in files:
        result.append({
            "id": file["id"],
            "filename": file["filename"],
            "subject": file["subject"],
            "file_url": file["file_url"],
            "file_size": file["file_size"],
            "file_type": file["file_type"],
            "created_at": file["created_at"]
        })
    return result

@app.get("/search/")
async def search_files(query: str, subject: str = None, file_type: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        sql = '''
            SELECT id, filename, subject, file_url, file_size, file_type, created_at 
            FROM files WHERE (filename LIKE :query OR subject LIKE :query)
        '''
        params = {'query': f'%{query}%'}
        
        if subject and subject != "All Subjects":
            sql += " AND subject = :subject"
            params['subject'] = subject
        
        if file_type:
            sql += " AND file_type = :file_type"
            params['file_type'] = file_type
        
        sql += " ORDER BY created_at DESC"
        
        cursor = await db.execute(sql, params)
        files = await cursor.fetchall()

    result = []
    for file in files:
        result.append({
            "id": file["id"],
            "filename": file["filename"],
            "subject": file["subject"],
            "file_url": file["file_url"],
            "file_size": file["file_size"],
            "file_type": file["file_type"],
            "created_at": file["created_at"]
        })
    return result

@app.get("/stats")
async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        total_files_cursor = await db.execute("SELECT COUNT(*) FROM files")
        total_files = (await total_files_cursor.fetchone())[0]
        
        total_subjects_cursor = await db.execute("SELECT COUNT(DISTINCT subject) FROM files")
        total_subjects = (await total_subjects_cursor.fetchone())[0]
    
    return {
        "total_files": total_files,
        "total_subjects": total_subjects,
        "active_users": 1 # Placeholder for active users
    }

@app.get("/uploads/{filename}")
async def get_upload(filename: str):
    """Serves an uploaded file."""
    file_path = UPLOADS_DIR / filename
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)