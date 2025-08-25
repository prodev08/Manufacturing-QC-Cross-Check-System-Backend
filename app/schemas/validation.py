from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from app.models.validation import ValidationStatus, CheckType


class ValidationResultBase(BaseModel):
    check_type: CheckType
    status: ValidationStatus
    description: str


class ValidationResultResponse(ValidationResultBase):
    id: UUID
    session_id: UUID
    source_files: Optional[List[str]] = None
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None
    details: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ValidationSummary(BaseModel):
    total_checks: int
    passed: int
    warnings: int
    failed: int
    overall_result: Optional[str] = None
