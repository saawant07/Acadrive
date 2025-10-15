from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class FileBase(BaseModel):
    filename: str
    subject: str  # Course name

class FileCreate(FileBase):
    pass

class File(FileBase):
    id: int
    file_url: str
    file_size: int
    preview_url: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True  # Updated from orm_mode