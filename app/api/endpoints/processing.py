from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.models.session import Session as SessionModel, SessionStatus
from app.models.file import UploadedFile
from app.services.file_processor import FileProcessor

router = APIRouter()
file_processor = FileProcessor()


@router.post('/process/{session_id}', response_model=Dict[str, Any])
async def process_session_files(
    session_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Trigger processing of all files in a session"""
    try:
        # Verify session exists
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'Session {session_id} not found'
            )
        
        # Check if session has files
        file_count = db.query(UploadedFile).filter(
            UploadedFile.session_id == session_id
        ).count()
        
        if file_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Session has no files to process'
            )
        
        # Update session status
        session.status = SessionStatus.PROCESSING
        db.commit()
        
        # Start background processing
        background_tasks.add_task(
            process_files_background,
            str(session_id)
        )
        
        return {
            'message': 'File processing started',
            'session_id': str(session_id),
            'status': 'processing',
            'file_count': file_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to start processing: {str(e)}'
        )


@router.get('/status/{session_id}', response_model=Dict[str, Any])
async def get_processing_status(
    session_id: UUID,
    db: Session = Depends(get_db)
):
    """Get processing status for a session"""
    try:
        # Verify session exists
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'Session {session_id} not found'
            )
        
        # Get processing summary
        summary = file_processor.get_processing_summary(str(session_id), db)
        
        return {
            'session_id': str(session_id),
            'session_status': session.status.value,
            'processing_summary': summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to get processing status: {str(e)}'
        )


@router.post('/process-file/{file_id}', response_model=Dict[str, Any])
async def process_single_file(
    file_id: UUID,
    db: Session = Depends(get_db)
):
    """Process a single file"""
    try:
        # Get file record
        file_record = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
        if not file_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'File {file_id} not found'
            )
        
        # Process the file
        result = file_processor.process_file(file_record, db)
        
        return {
            'file_id': str(file_id),
            'filename': file_record.filename,
            'processing_result': result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to process file: {str(e)}'
        )


async def process_files_background(session_id: str):
    """Background task to process all files in a session"""
    from app.database import SessionLocal
    
    db = SessionLocal()
    try:
        # Process all files
        result = file_processor.process_session_files(session_id, db)
        
        # Update session status based on results
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if session:
            if result['success'] and result['failed_count'] == 0:
                session.status = SessionStatus.COMPLETED
            else:
                session.status = SessionStatus.FAILED
            db.commit()
            
    except Exception as e:
        # Mark session as failed
        try:
            session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
            if session:
                session.status = SessionStatus.FAILED
                db.commit()
        except:
            pass
            
    finally:
        db.close()
