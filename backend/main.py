import os
import aiosqlite
import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import re
import cloudinary
from pydantic import BaseModel

# Setup
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "acadrive.db"

# Cloudinary Configuration - expecting environment variables
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
    secure=True
)

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

# Pydantic Models for request body validation
class FileUploadData(BaseModel):
    subject: str
    file_url: str
    filename: str
    file_size: int
    file_type: str

def init_db():
    """Initializes the SQLite database and creates the files table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # This is a one-time sync operation, so standard sqlite3 is fine here.
    conn.execute('''CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            subject TEXT NOT NULL,
            file_path TEXT,
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

@app.get("/config")
async def get_config():
    """Provides the Cloudinary cloud name to the frontend."""
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME")
    if not cloud_name:
        raise HTTPException(status_code=500, detail="Cloudinary configuration is missing on the server.")
    return {"cloud_name": cloud_name}

@app.post("/upload/", status_code=201)
async def save_file_record(data: FileUploadData):
    """Saves the metadata of a file already uploaded to Cloudinary."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                '''INSERT INTO files (filename, subject, file_path, file_url, file_size, file_type) VALUES (?, ?, ?, ?, ?, ?)''',
                (data.filename, data.subject, "cloudinary", data.file_url, data.file_size, data.file_type)
            )
            await db.commit()
            file_id = cursor.lastrowid
        
        return {
            "id": file_id,
            "filename": data.filename,
            "subject": data.subject,
            "file_url": data.file_url,
            "file_size": data.file_size,
            "file_type": data.file_type
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
async def search_files(query: str, subject: Optional[str] = None, file_type: Optional[str] = None):
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
        
        if file_type and file_type != "All Types":
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

@app.get("/subjects")
async def get_subjects():
    """Returns a list of unique subjects from the database."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT DISTINCT subject FROM files ORDER BY subject ASC")
        subjects = await cursor.fetchall()
    return [subject[0] for subject in subjects]