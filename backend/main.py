import os
import aiofiles
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
from database import get_db, FileRecord

# --- SETUP ---
# Get the directory where this main.py file is located
BACKEND_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BACKEND_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Acadrive API", version="1.0.0")

# --- CORS MIDDLEWARE ---
# Allow all origins for now - you can restrict later
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this to your Vercel domain later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DATABASE DEPENDENCY ---
def get_database():
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

# --- API ENDPOINTS ---

@app.post("/upload/")
async def upload_file(
    subject: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_database)
):
    try:
        # Validate file size (50MB limit)
        max_size = 50 * 1024 * 1024  # 50MB in bytes
        file_content = await file.read()
        
        if len(file_content) > max_size:
            raise HTTPException(status_code=400, detail="File too large. Maximum size is 50MB.")
        
        # Define the path where the file will be saved
        file_path = UPLOADS_DIR / file.filename
        
        # Check if file already exists and create unique name
        counter = 1
        original_name = file.filename
        name_parts = original_name.rsplit('.', 1)
        
        while file_path.exists():
            if len(name_parts) == 2:
                new_filename = f"{name_parts[0]}_{counter}.{name_parts[1]}"
            else:
                new_filename = f"{original_name}_{counter}"
            file_path = UPLOADS_DIR / new_filename
            counter += 1
        
        # Save the file
        async with aiofiles.open(file_path, 'wb') as out_file:
            await out_file.write(file_content)
        
        file_size = len(file_content)
        file_type = file.content_type.split('/')[0] if file.content_type else 'application'
        
        # Use the final filename (which might be modified for uniqueness)
        final_filename = file_path.name
        
        # Create a database record
        db_file = FileRecord(
            filename=final_filename,
            subject=subject,
            file_path=str(file_path),
            file_url=f"/uploads/{final_filename}",
            file_size=file_size,
            file_type=file_type
        )
        db.add(db_file)
        db.commit()
        db.refresh(db_file)
        
        return {
            "id": db_file.id,
            "filename": db_file.filename,
            "subject": db_file.subject,
            "file_url": f"https://{os.environ.get('RAILWAY_STATIC_URL', '')}/uploads/{final_filename}",
            "file_size": db_file.file_size,
            "file_type": db_file.file_type,
            "created_at": db_file.created_at
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/recent")
def get_recent_files(db: Session = Depends(get_database)):
    files = db.query(FileRecord).order_by(FileRecord.created_at.desc()).limit(5).all()
    
    # Build full URLs for files
    base_url = f"https://{os.environ.get('RAILWAY_STATIC_URL', '')}"
    for file in files:
        file.file_url = f"{base_url}{file.file_url}"
    
    return files

@app.get("/search/")
def search_files(query: str, subject: str = None, file_type: str = None, db: Session = Depends(get_database)):
    search_query = db.query(FileRecord)
    
    # Filter by the main search text
    search_filter = f"%{query}%"
    search_query = search_query.filter(
        (FileRecord.filename.ilike(search_filter)) |
        (FileRecord.subject.ilike(search_filter))
    )
    
    # Add filters from the dropdowns if they exist
    if subject:
        search_query = search_query.filter(FileRecord.subject == subject)
    
    if file_type:
        search_query = search_query.filter(FileRecord.file_type == file_type)
    
    files = search_query.order_by(FileRecord.created_at.desc()).all()
    
    # Build full URLs for files
    base_url = f"https://{os.environ.get('RAILWAY_STATIC_URL', '')}"
    for file in files:
        file.file_url = f"{base_url}{file.file_url}"
        
    return files

@app.get("/stats")
def get_stats(db: Session = Depends(get_database)):
    total_files = db.query(FileRecord).count()
    total_subjects = db.query(FileRecord.subject).distinct().count()
    return {
        "total_files": total_files,
        "total_subjects": total_subjects,
        "active_users": 1  # Placeholder for now
    }

# --- SERVING UPLOADED FILES ---
@app.get("/uploads/{filename}")
async def get_uploaded_file(filename: str):
    file_path = UPLOADS_DIR / filename
    if file_path.is_file():
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="File not found")

# Health check endpoint
@app.get("/")
async def root():
    return {"message": "Acadrive API is running", "status": "healthy"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "acadrive-api"}