from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.models.session import Session as SessionModel
from app.services.workflow import QCWorkflow

router = APIRouter()
workflow = QCWorkflow()


@router.post('/analyze/{session_id}', response_model=Dict[str, Any])
async def run_complete_analysis(
    session_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Run complete QC analysis (process files + validate)"""
    try:
        # Verify session exists
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'Session {session_id} not found'
            )
        
        # Start background analysis
        background_tasks.add_task(
            run_analysis_background,
            session_id
        )
        
        return {
            'message': 'Complete QC analysis started',
            'session_id': str(session_id),
            'status': 'analyzing'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to start analysis: {str(e)}'
        )


@router.post('/analyze-now/{session_id}', response_model=Dict[str, Any])
async def run_complete_analysis_now(
    session_id: UUID,
    db: Session = Depends(get_db)
):
    """Run complete QC analysis immediately (synchronous)"""
    try:
        # Verify session exists
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'Session {session_id} not found'
            )
        
        # Run analysis
        result = workflow.run_complete_analysis(session_id, db)
        
        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result['error']
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Analysis failed: {str(e)}'
        )


@router.get('/status/{session_id}', response_model=Dict[str, Any])
async def get_workflow_status(
    session_id: UUID,
    db: Session = Depends(get_db)
):
    """Get comprehensive workflow status for a session"""
    try:
        status_info = workflow.get_workflow_status(session_id, db)
        
        if 'error' in status_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=status_info['error']
            )
        
        return status_info
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to get workflow status: {str(e)}'
        )


@router.post('/retry/{session_id}', response_model=Dict[str, Any])
async def retry_failed_processing(
    session_id: UUID,
    db: Session = Depends(get_db)
):
    """Retry processing for failed files"""
    try:
        # Verify session exists
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'Session {session_id} not found'
            )
        
        result = workflow.retry_failed_processing(session_id, db)
        
        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result['error']
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to retry processing: {str(e)}'
        )


async def run_analysis_background(session_id: UUID):
    """Background task to run complete analysis"""
    from app.database import SessionLocal
    
    db = SessionLocal()
    try:
        workflow.run_complete_analysis(session_id, db)
    except Exception as e:
        # Log error but don't raise - this is a background task
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Background analysis failed for session {session_id}: {str(e)}')
    finally:
        db.close()
