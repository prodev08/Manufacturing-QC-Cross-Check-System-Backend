import os
import uuid
import shutil
from typing import List
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.config import settings
from app.models.session import Session as SessionModel
from app.models.file import UploadedFile as FileModel, FileType
from app.schemas.file import FileUploadResponse, FileResponse
from app.api.deps import validate_file_size, validate_file_type

router = APIRouter()


def get_file_type_from_mime(mime_type: str) -> FileType:
    """Determine file type from MIME type"""
    if mime_type in settings.allowed_pdf_types:
        return FileType.TRAVELER_PDF
    elif mime_type in settings.allowed_image_types:
        return FileType.PRODUCT_IMAGE
    elif mime_type in settings.allowed_excel_types:
        return FileType.BOM_EXCEL
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Unsupported file type: {mime_type}'
        )


def save_uploaded_file(file: UploadFile, session_id: UUID) -> tuple[str, str]:
    """Save uploaded file to disk and return file path and generated filename"""
    # Create session directory
    session_dir = Path(settings.upload_dir) / str(session_id)
    session_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    file_extension = Path(file.filename).suffix
    unique_filename = f'{uuid.uuid4()}{file_extension}'
    file_path = session_dir / unique_filename
    
    # Save file
    try:
        with open(file_path, 'wb') as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to save file: {str(e)}'
        )
    
    return str(file_path), unique_filename


@router.post('/upload/{session_id}', response_model=List[FileUploadResponse])
async def upload_files(
    session_id: UUID,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """Upload multiple files to a session"""
    
    # Verify session exists
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Session {session_id} not found'
        )
    
    uploaded_files = []
    
    try:
        for file in files:
            # Validate file
            validate_file_size(file.size, settings.max_file_size)
            
            # Determine file type
            file_type = get_file_type_from_mime(file.content_type)
            
            # Validate file type
            if file_type == FileType.TRAVELER_PDF:
                validate_file_type(file.content_type, settings.allowed_pdf_types)
            elif file_type == FileType.PRODUCT_IMAGE:
                validate_file_type(file.content_type, settings.allowed_image_types)
            elif file_type == FileType.BOM_EXCEL:
                validate_file_type(file.content_type, settings.allowed_excel_types)
            
            # Save file to disk
            file_path, unique_filename = save_uploaded_file(file, session_id)
            
            # Create database record
            db_file = FileModel(
                session_id=session_id,
                filename=unique_filename,
                original_filename=file.filename,
                file_type=file_type,
                file_size=file.size,
                mime_type=file.content_type,
                file_path=file_path
            )
            
            db.add(db_file)
            db.flush()  # Get the ID without committing
            
            uploaded_files.append(FileUploadResponse(
                file_id=db_file.id,
                filename=db_file.filename,
                file_type=db_file.file_type,
                status='uploaded',
                message=f'File uploaded successfully'
            ))
        
        # Commit all files at once
        db.commit()
        
        return uploaded_files
        
    except HTTPException:
        db.rollback()
        # Clean up any files that were saved
        for response in uploaded_files:
            try:
                file_record = db.query(FileModel).filter(FileModel.id == response.file_id).first()
                if file_record and os.path.exists(file_record.file_path):
                    os.remove(file_record.file_path)
            except:
                pass  # Best effort cleanup
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to upload files: {str(e)}'
        )


@router.get('/session/{session_id}', response_model=List[FileResponse])
async def get_session_files(
    session_id: UUID,
    db: Session = Depends(get_db)
):
    """Get all files for a specific session"""
    try:
        # Verify session exists
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'Session {session_id} not found'
            )
        
        files = db.query(FileModel).filter(FileModel.session_id == session_id).all()
        return files
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to retrieve files: {str(e)}'
        )


@router.get('/{file_id}', response_model=FileResponse)
async def get_file(
    file_id: UUID,
    db: Session = Depends(get_db)
):
    """Get information about a specific file"""
    try:
        file = db.query(FileModel).filter(FileModel.id == file_id).first()
        if not file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'File {file_id} not found'
            )
        
        return file
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to retrieve file: {str(e)}'
        )


@router.delete('/{file_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete a file and remove it from disk"""
    try:
        file = db.query(FileModel).filter(FileModel.id == file_id).first()
        if not file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'File {file_id} not found'
            )
        
        # Remove file from disk
        if os.path.exists(file.file_path):
            os.remove(file.file_path)
        
        # Remove from database
        db.delete(file)
        db.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to delete file: {str(e)}'
        )
