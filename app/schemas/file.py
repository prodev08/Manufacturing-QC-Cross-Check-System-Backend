from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID

from app.models.file import FileType, ProcessingStatus


class FileBase(BaseModel):
    filename: str
    file_type: FileType


class FileResponse(FileBase):
    id: UUID
    session_id: UUID
    original_filename: str
    file_size: int
    mime_type: str
    processing_status: ProcessingStatus
    processing_error: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class FileUploadResponse(BaseModel):
    file_id: UUID
    filename: str
    file_type: FileType
    status: str
    message: str
