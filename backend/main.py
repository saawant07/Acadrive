import os
import aiofiles
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
from database import get_db, FileRecord

# Setup
BACKEND_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BACKEND_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Acadrive API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_database():
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

@app.get("/")
async def root():
    return {"message": "Acadrive API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/upload/")
async def upload_file(
    subject: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_database)
):
    try:
        # Read file
        content = await file.read()
        file_size = len(content)
        
        # Validate size
        if file_size > 50 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large")
        
        # Create safe filename
        safe_filename = file.filename
        file_path = UPLOADS_DIR / safe_filename
        
        # Handle duplicates
        counter = 1
        name_parts = safe_filename.rsplit('.', 1)
        while file_path.exists():
            if len(name_parts) == 2:
                new_filename = f"{name_parts[0]}_{counter}.{name_parts[1]}"
            else:
                new_filename = f"{safe_filename}_{counter}"
            file_path = UPLOADS_DIR / new_filename
            counter += 1
        
        final_filename = file_path.name
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as out_file:
            await out_file.write(content)
        
        # Determine file type
        file_type = 'document'
        if final_filename.lower().endswith('.pdf'):
            file_type = 'pdf'
        elif final_filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            file_type = 'image'
        
        # Create database record
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
            "file_url": f"/uploads/{final_filename}",
            "file_size": db_file.file_size,
            "file_type": db_file.file_type
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/recent")
def get_recent_files(db: Session = Depends(get_database)):
    files = db.query(FileRecord).order_by(FileRecord.created_at.desc()).limit(5).all()
    return files

@app.get("/search/")
def search_files(query: str, subject: str = None, file_type: str = None, db: Session = Depends(get_database)):
    search_query = db.query(FileRecord)
    
    if query:
        search_filter = f"%{query}%"
        search_query = search_query.filter(
            (FileRecord.filename.ilike(search_filter)) |
            (FileRecord.subject.ilike(search_filter))
        )
    
    if subject:
        search_query = search_query.filter(FileRecord.subject == subject)
    
    if file_type:
        search_query = search_query.filter(FileRecord.file_type == file_type)
    
    return search_query.order_by(FileRecord.created_at.desc()).all()

@app.get("/stats")
def get_stats(db: Session = Depends(get_database)):
    total_files = db.query(FileRecord).count()
    total_subjects = db.query(FileRecord.subject).distinct().count()
    return {
        "total_files": total_files,
        "total_subjects": total_subjects,
        "active_users": 1
    }

@app.get("/uploads/{filename}")
async def get_uploaded_file(filename: str):
    file_path = UPLOADS_DIR / filename
    if file_path.is_file():
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="File not found")