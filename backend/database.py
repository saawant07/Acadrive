import os
from sqlmodel import SQLModel, Field, create_engine, Session
from typing import Optional
from datetime import datetime
from sqlalchemy import Column, DateTime, text

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///./acadrive.db')

if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

engine = create_engine(DATABASE_URL)

class FileRecord(SQLModel, table=True):
    __tablename__ = "files"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str
    subject: str
    file_path: str
    file_url: str
    file_size: int
    file_type: str
    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=text('CURRENT_TIMESTAMP'))
    )

# Create tables
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

# Initialize database
create_db_and_tables()