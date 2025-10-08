import os
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# STEP 1: Load the environment variables from .env FIRST.
load_dotenv(dotenv_path="backend/.env")

# STEP 2: Now, import the other project files that NEED the variables.
from . import models, schemas
from .database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

cloudinary.config(
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key = os.getenv("CLOUDINARY_API_KEY"),
    api_secret = os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

@app.post("/upload/", response_model=schemas.File)
def upload_file(
    subject: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)

        # For this final version, we will always upload PDFs as "image" resource type
        # to allow us to generate a preview.
        upload_result = cloudinary.uploader.upload(
            file.file, 
            resource_type="image", 
            folder="acadrive_files"
        )
        
        secure_url = upload_result.get("secure_url")
        if not secure_url:
            raise HTTPException(status_code=500, detail="Could not upload file.")
        
        # By default, the URLs are the one Cloudinary gives us (for images)
        viewable_url = secure_url
        preview_url = secure_url

        # --- FINAL LOGIC FOR PDFs ---
        # If the file is a PDF, we generate two special URLs
        if "pdf" in file.content_type:
            # 1. For the preview, we create a JPG of the first page.
            preview_url = secure_url.replace("/upload/", "/upload/pg_1/f_jpg/")
            # 2. For the main link, we change "image" to "raw" to make it viewable.
            viewable_url = secure_url.replace("/image/upload/", "/raw/upload/")
        # --- END OF LOGIC ---

        db_file = models.FileRecord(
            filename=file.filename, 
            subject=subject, 
            file_url=viewable_url,     # Store the corrected, viewable URL
            file_size=file_size,
            preview_url=preview_url   # Store the generated preview URL
        )
        db.add(db_file)
        db.commit()
        db.refresh(db_file)
        return db_file
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/search/", response_model=list[schemas.File])
def search_files(query: str, db: Session = Depends(get_db)):
    search_query = f"%{query}%"
    files = db.query(models.FileRecord).filter(
        (models.FileRecord.filename.ilike(search_query)) |
        (models.FileRecord.subject.ilike(search_query))
    ).all()
    return files
# Add this new function to your main.py file

@app.get("/files/recent", response_model=list[schemas.File])
def get_recent_files(db: Session = Depends(get_db)):
    # Query the database for files
    # Order them by creation date in descending order (newest first)
    # Limit the result to the top 5
    recent_files = db.query(models.FileRecord).order_by(
        models.FileRecord.created_at.desc()
    ).limit(5).all()
    
    return recent_files
@app.get("/health")
def health_check():
    return {"status": "ok"}