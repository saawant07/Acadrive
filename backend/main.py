import os
import aiofiles
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, distinct
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel # Import BaseModel
from dotenv import load_dotenv # Import load_dotenv

# Import database setup and model
from database import get_db, FileRecord, init_db

# --- SETUP ---
load_dotenv() # Load variables from .env file

# Get the directory where this main.py file is located
BACKEND_DIR = Path(__file__).resolve().parent
# Define the directory to store uploads within the backend folder
UPLOADS_DIR = BACKEND_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True) # Create the folder if it doesn't exist

# Initialize database tables on startup
init_db()

app = FastAPI(title="Acadrive API")

# --- MIDDLEWARE (For CORS) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Model for JSON Request ---
class FileUploadRequest(BaseModel):
    subject: str
    file_url: str
    filename: str
    file_size: int
    file_type: str

# --- API ENDPOINTS ---

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# NEW: /config endpoint for frontend
@app.get("/config")
async def get_config():
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
    if not cloud_name:
        raise HTTPException(status_code=500, detail="Cloudinary config not set")
    return {"cloud_name": cloud_name}

# UPDATED: /upload/ endpoint to accept JSON
@app.post("/upload/")
async def upload_file(
    upload_data: FileUploadRequest, # Use the Pydantic model
    db: Session = Depends(get_db)
):
    try:
        # We are receiving data *after* it's on Cloudinary
        # The file_path is now the remote URL
        db_file = FileRecord(
            filename=upload_data.filename,
            subject=upload_data.subject,
            file_path=upload_data.file_url, # Store the Cloudinary URL
            file_url=upload_data.file_url,  # Store the Cloudinary URL
            file_size=upload_data.file_size,
            file_type=upload_data.file_type
        )
        db.add(db_file)
        db.commit()
        db.refresh(db_file)
        
        # Return data matching frontend expectations
        return {
            "id": db_file.id, "filename": db_file.filename, "subject": db_file.subject,
            "file_url": db_file.file_url, "file_size": db_file.file_size,
            "file_type": db_file.file_type, "created_at": db_file.created_at
        }
    except Exception as e:
        print(f"Error during upload processing: {e}") 
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.get("/files/recent")
def get_recent_files(db: Session = Depends(get_db)):
    return db.query(FileRecord).order_by(FileRecord.created_at.desc()).limit(4).all()

@app.get("/search/")
def search_files(query: Optional[str] = None, subject: Optional[str] = None, file_type: Optional[str] = None, db: Session = Depends(get_db)):
    search_query = db.query(FileRecord)
    
    if query:
        search_filter = f"%{query}%"
        search_query = search_query.filter(
            or_(
                FileRecord.filename.ilike(search_filter),
                FileRecord.subject.ilike(search_filter)
            )
        )
    if subject and subject != "All Subjects": 
        search_query = search_query.filter(FileRecord.subject == subject)
    if file_type and file_type != "All Types": 
        search_query = search_query.filter(FileRecord.file_type == file_type)
        
    return search_query.order_by(FileRecord.created_at.desc()).all()

@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    total_files = db.query(FileRecord).count()
    total_subjects = db.query(distinct(FileRecord.subject)).count()
    return {
        "total_files": total_files,
        "total_subjects": total_subjects,
        "active_users": "1" # Placeholder
    }

@app.get("/subjects")
def get_subjects(db: Session = Depends(get_db)):
    subjects = db.query(distinct(FileRecord.subject)).order_by(FileRecord.subject.asc()).all()
    return [subject[0] for subject in subjects if subject[0]]


# --- SERVING STATIC FILES ---
# We remove serving local /uploads/ files, as they are now on Cloudinary
# We keep serving the frontend for local testing

# Mounts the 'frontend' directory to serve index.html etc. at the root URL
app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")

# Allows running the server directly with 'python3 backend/main.py'
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)