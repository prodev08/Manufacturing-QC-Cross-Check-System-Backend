from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from app.schemas.file import FileResponse
from app.schemas.validation import ValidationResultResponse
from app.models.session import SessionStatus, OverallResult


class SessionBase(BaseModel):
    pass


class SessionCreate(SessionBase):
    pass


class SessionResponse(SessionBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    status: SessionStatus
    overall_result: Optional[OverallResult] = None
    
    class Config:
        from_attributes = True


class SessionWithFiles(SessionResponse):
    files: List['FileResponse'] = []
    validation_results: List['ValidationResultResponse'] = []
    
    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    sessions: List[SessionResponse]
    total: int
    page: int
    per_page: int

SessionWithFiles.model_rebuild()
