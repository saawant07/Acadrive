from pydantic import BaseModel
from datetime import datetime

class FileBase(BaseModel):
    filename: str
    subject: str

class File(FileBase):
    id: int
    file_url: str
    file_size: int
    preview_url: str | None = None
    created_at: datetime
    class Config:
        orm_mode = True