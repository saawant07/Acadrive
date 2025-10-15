from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class FileRecord(Base):
    __tablename__ = "files"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False)  # Course name from user
    file_url = Column(Text, nullable=False)
    file_size = Column(Integer, nullable=False)
    preview_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())