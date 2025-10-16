import os
import aiofiles
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from pathlib import Path

# Database imports
from database import get_db, FileRecord, Base, engine

# Create tables
Base.metadata.create_all(bind=engine)

# --- SETUP ---
BACKEND_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BACKEND_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Acadrive API", version="1.0.0")

# --- CORS MIDDLEWARE ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in production
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

# --- HEALTH CHECK ---
@app.get("/")
async def root():
    return {"message": "Acadrive API is running", "status": "healthy"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "acadrive-api"}

# --- API ENDPOINTS ---
@app.post("/upload/")
async def upload_file(
    subject: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_database)
):
    try:
        print(f"Uploading file: {file.filename} for subject: {subject}")
        
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Validate file size (50MB limit)
        max_size = 50 * 1024 * 1024
        if file_size > max_size:
            raise HTTPException(status_code=400, detail="File too large. Maximum size is 50MB.")
        
        # Create safe filename
        safe_filename = "".join(c for c in file.filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
        if not safe_filename:
            safe_filename = "uploaded_file"
        
        file_path = UPLOADS_DIR / safe_filename
        
        # Handle duplicate filenames
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
        if final_filename.lower().endswith(('.pdf')):
            file_type = 'pdf'
        elif final_filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
            file_type = 'image'
        elif final_filename.lower().endswith(('.doc', '.docx')):
            file_type = 'document'
        elif final_filename.lower().endswith(('.ppt', '.pptx')):
            file_type = 'presentation'
        
        # Get base URL for file links
        render_url = os.environ.get('RENDER_EXTERNAL_URL', '')
        base_url = render_url if render_url else ""
        
        # Create database record
        db_file = FileRecord(
            filename=final_filename,
            subject=subject,
            file_path=str(file_path),
            file_url=f"{base_url}/uploads/{final_filename}",
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
            "file_url": db_file.file_url,
            "file_size": db_file.file_size,
            "file_type": db_file.file_type,
            "created_at": db_file.created_at.isoformat() if db_file.created_at else None
        }
        
    except Exception as e:
        print(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/recent")
def get_recent_files(db: Session = Depends(get_database)):
    try:
        files = db.query(FileRecord).order_by(FileRecord.created_at.desc()).limit(5).all()
        
        # Build response with proper URLs
        result = []
        for file in files:
            result.append({
                "id": file.id,
                "filename": file.filename,
                "subject": file.subject,
                "file_url": file.file_url,
                "file_size": file.file_size,
                "file_type": file.file_type,
                "created_at": file.created_at.isoformat() if file.created_at else None
            })
        
        return result
    except Exception as e:
        print(f"Error fetching recent files: {str(e)}")
        return []

@app.get("/search/")
def search_files(query: str, subject: str = None, file_type: str = None, db: Session = Depends(get_database)):
    try:
        search_query = db.query(FileRecord)
        
        # Filter by search query
        if query:
            search_filter = f"%{query}%"
            search_query = search_query.filter(
                (FileRecord.filename.ilike(search_filter)) |
                (FileRecord.subject.ilike(search_filter))
            )
        
        # Apply filters
        if subject and subject != "All Subjects":
            search_query = search_query.filter(FileRecord.subject == subject)
        
        if file_type and file_type != "All Types":
            search_query = search_query.filter(FileRecord.file_type == file_type)
        
        files = search_query.order_by(FileRecord.created_at.desc()).all()
        
        # Build response
        result = []
        for file in files:
            result.append({
                "id": file.id,
                "filename": file.filename,
                "subject": file.subject,
                "file_url": file.file_url,
                "file_size": file.file_size,
                "file_type": file.file_type,
                "created_at": file.created_at.isoformat() if file.created_at else None
            })
        
        return result
    except Exception as e:
        print(f"Search error: {str(e)}")
        return []

@app.get("/stats")
def get_stats(db: Session = Depends(get_database)):
    try:
        total_files = db.query(FileRecord).count()
        total_subjects = db.query(FileRecord.subject).distinct().count()
        return {
            "total_files": total_files,
            "total_subjects": total_subjects,
            "active_users": 1
        }
    except Exception as e:
        print(f"Stats error: {str(e)}")
        return {"total_files": 0, "total_subjects": 0, "active_users": 0}

@app.get("/uploads/{filename}")
async def get_uploaded_file(filename: str):
    try:
        file_path = UPLOADS_DIR / filename
        if file_path.is_file():
            return FileResponse(file_path)
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)