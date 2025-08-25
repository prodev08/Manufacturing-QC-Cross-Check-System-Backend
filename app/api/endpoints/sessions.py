from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.models.session import Session as SessionModel
from app.schemas.session import SessionCreate, SessionResponse, SessionWithFiles, SessionListResponse

router = APIRouter()


@router.post('/', response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    session_data: SessionCreate,
    db: Session = Depends(get_db)
):
    """Create a new QC analysis session"""
    try:
        # Create new session
        db_session = SessionModel()
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
        
        return db_session
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to create session: {str(e)}'
        )


@router.get('/', response_model=SessionListResponse)
async def list_sessions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all QC analysis sessions with pagination"""
    try:
        sessions = db.query(SessionModel).offset(skip).limit(limit).all()
        total = db.query(SessionModel).count()
        
        return SessionListResponse(
            sessions=sessions,
            total=total,
            page=skip // limit + 1,
            per_page=limit
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to retrieve sessions: {str(e)}'
        )


@router.get('/{session_id}', response_model=SessionWithFiles)
async def get_session(
    session_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific session with files and validation results"""
    try:
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'Session {session_id} not found'
            )
        
        return session
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to retrieve session: {str(e)}'
        )


@router.delete('/{session_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete a session and all associated files and results"""
    try:
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'Session {session_id} not found'
            )
        
        db.delete(session)
        db.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to delete session: {str(e)}'
        )
