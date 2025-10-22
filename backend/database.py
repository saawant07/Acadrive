import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from pathlib import Path
from dotenv import load_dotenv

# Load .env file for local development
load_dotenv()

# Use PostgreSQL URL from environment variables
# Fallback to local SQLite for local testing if DATABASE_URL is not set
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{Path(__file__).resolve().parent / 'acadrive.db'}")

# Create database engine
# connect_args is only for SQLite
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for database models
Base = declarative_base()

# Define the 'files' table structure
class FileRecord(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False) # Path on server (or remote URL)
    file_url = Column(Text, nullable=False) # URL to access file
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(50), nullable=False) # e.g., 'image', 'pdf'
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# Function to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Function to create the database and table
def init_db():
    Base.metadata.create_all(bind=engine)