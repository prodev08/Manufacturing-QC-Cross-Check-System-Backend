from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db


def get_database() -> Session:
    """Get database session dependency"""
    return Depends(get_db)


def validate_file_size(file_size: int, max_size: int = 50_000_000) -> bool:
    """Validate file size is within limits"""
    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f'File size ({file_size} bytes) exceeds maximum allowed size ({max_size} bytes)'
        )
    return True


def validate_file_type(mime_type: str, allowed_types: set) -> bool:
    """Validate file MIME type is allowed"""
    if mime_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'File type {mime_type} is not allowed. Allowed types: {allowed_types}'
        )
    return True
