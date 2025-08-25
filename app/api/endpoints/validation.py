from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.models.session import Session as SessionModel
from app.models.validation import ValidationResult
from app.schemas.validation import ValidationResultResponse, ValidationSummary
from app.services.validator import QCValidator

router = APIRouter()
validator = QCValidator()


@router.post('/validate/{session_id}', response_model=Dict[str, Any])
async def validate_session(
    session_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Trigger validation for a session"""
    try:
        # Verify session exists
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'Session {session_id} not found'
            )
        
        # Start background validation
        background_tasks.add_task(
            validate_session_background,
            session_id
        )
        
        return {
            'message': 'Validation started',
            'session_id': str(session_id),
            'status': 'validating'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to start validation: {str(e)}'
        )


@router.post('/validate-now/{session_id}', response_model=Dict[str, Any])
async def validate_session_now(
    session_id: UUID,
    db: Session = Depends(get_db)
):
    """Perform immediate validation for a session"""
    try:
        # Verify session exists
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'Session {session_id} not found'
            )
        
        # Perform validation
        result = validator.validate_session(session_id, db)
        
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
            detail=f'Validation failed: {str(e)}'
        )


@router.get('/results/{session_id}', response_model=List[ValidationResultResponse])
async def get_validation_results(
    session_id: UUID,
    db: Session = Depends(get_db)
):
    """Get validation results for a session"""
    try:
        # Verify session exists
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'Session {session_id} not found'
            )
        
        # Get validation results
        results = db.query(ValidationResult).filter(
            ValidationResult.session_id == session_id
        ).order_by(ValidationResult.created_at.desc()).all()
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to retrieve validation results: {str(e)}'
        )


@router.get('/summary/{session_id}', response_model=ValidationSummary)
async def get_validation_summary(
    session_id: UUID,
    db: Session = Depends(get_db)
):
    """Get validation summary for a session"""
    try:
        # Verify session exists
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'Session {session_id} not found'
            )
        
        # Get validation results
        results = db.query(ValidationResult).filter(
            ValidationResult.session_id == session_id
        ).all()
        
        # Calculate summary
        total_checks = len(results)
        passed = len([r for r in results if r.status.value == 'PASS'])
        warnings = len([r for r in results if r.status.value == 'WARNING'])
        failed = len([r for r in results if r.status.value == 'FAIL'])
        
        return ValidationSummary(
            total_checks=total_checks,
            passed=passed,
            warnings=warnings,
            failed=failed,
            overall_result=session.overall_result.value if session.overall_result else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to get validation summary: {str(e)}'
        )


@router.get('/result/{result_id}', response_model=ValidationResultResponse)
async def get_validation_result(
    result_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific validation result"""
    try:
        result = db.query(ValidationResult).filter(ValidationResult.id == result_id).first()
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'Validation result {result_id} not found'
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to retrieve validation result: {str(e)}'
        )


@router.delete('/results/{session_id}', status_code=status.HTTP_204_NO_CONTENT)
async def clear_validation_results(
    session_id: UUID,
    db: Session = Depends(get_db)
):
    """Clear all validation results for a session"""
    try:
        # Verify session exists
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'Session {session_id} not found'
            )
        
        # Delete validation results
        db.query(ValidationResult).filter(
            ValidationResult.session_id == session_id
        ).delete()
        
        # Reset session overall result
        session.overall_result = None
        
        db.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to clear validation results: {str(e)}'
        )


async def validate_session_background(session_id: UUID):
    """Background task to validate a session"""
    from app.database import SessionLocal
    
    db = SessionLocal()
    try:
        validator.validate_session(session_id, db)
    except Exception as e:
        # Log error but don't raise - this is a background task
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Background validation failed for session {session_id}: {str(e)}')
    finally:
        db.close()
