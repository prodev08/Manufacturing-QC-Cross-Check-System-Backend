import logging
from typing import Dict, Any
from sqlalchemy.orm import Session
from uuid import UUID

from app.models.session import Session as SessionModel, SessionStatus
from app.services.file_processor import FileProcessor
from app.services.validator import QCValidator

logger = logging.getLogger(__name__)


class QCWorkflow:
    """Service for orchestrating the complete QC analysis workflow"""
    
    def __init__(self):
        self.logger = logger
        self.file_processor = FileProcessor()
        self.validator = QCValidator()
    
    async def run_complete_analysis(self, session_id: UUID, db: Session) -> Dict[str, Any]:
        """Run the complete QC analysis workflow: process files then validate"""
        try:
            self.logger.info(f'Starting complete QC analysis for session: {session_id}')
            
            # Verify session exists
            session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
            if not session:
                raise ValueError(f'Session {session_id} not found')
            
            # Update session status
            session.status = SessionStatus.PROCESSING
            db.commit()
            
            # Step 1: Process all files
            self.logger.info(f'Step 1: Processing files for session {session_id}')
            processing_result = await self.file_processor.process_session_files(str(session_id), db)
            
            if not processing_result['success']:
                session.status = SessionStatus.FAILED
                db.commit()
                return {
                    'success': False,
                    'error': 'File processing failed',
                    'details': processing_result
                }
            
            # Check if any files failed processing
            if processing_result['failed_count'] > 0:
                self.logger.warning(f'Some files failed processing for session {session_id}')
            
            # Step 2: Validate cross-references
            self.logger.info(f'Step 2: Validating cross-references for session {session_id}')
            validation_result = self.validator.validate_session(session_id, db)
            
            if not validation_result['success']:
                session.status = SessionStatus.FAILED
                db.commit()
                return {
                    'success': False,
                    'error': 'Validation failed',
                    'details': validation_result
                }
            
            # Update session status to completed
            session.status = SessionStatus.COMPLETED
            db.commit()
            
            self.logger.info(f'Complete QC analysis finished for session {session_id}')
            
            return {
                'success': True,
                'session_id': str(session_id),
                'processing_result': processing_result,
                'validation_result': validation_result,
                'overall_result': validation_result.get('overall_result'),
                'summary': {
                    'files_processed': processing_result['processed_count'],
                    'files_successful': processing_result['successful_count'],
                    'files_failed': processing_result['failed_count'],
                    'validation_checks': validation_result['validation_count'],
                    'final_status': validation_result.get('overall_result')
                }
            }
            
        except Exception as e:
            self.logger.error(f'Complete QC analysis failed for session {session_id}: {str(e)}')
            
            # Update session status to failed
            try:
                session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
                if session:
                    session.status = SessionStatus.FAILED
                    db.commit()
            except Exception as db_error:
                self.logger.error(f'Failed to update session status: {str(db_error)}')
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_workflow_status(self, session_id: UUID, db: Session) -> Dict[str, Any]:
        """Get comprehensive status of the QC workflow for a session"""
        try:
            # Get session
            session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
            if not session:
                raise ValueError(f'Session {session_id} not found')
            
            # Get processing summary
            processing_summary = self.file_processor.get_processing_summary(str(session_id), db)
            
            # Get validation summary if available
            try:
                validator = QCValidator()
                validation_results = validator.get_validation_results(str(session_id), db)
                if validation_results:
                    validation_summary = {
                        'total_checks': len(validation_results),
                        'passed': len([r for r in validation_results if r.status.value == 'PASS']),
                        'warnings': len([r for r in validation_results if r.status.value == 'WARNING']),
                        'failures': len([r for r in validation_results if r.status.value == 'FAIL'])
                    }
                else:
                    validation_summary = None
            except:
                validation_summary = None
            
            # Determine workflow stage
            if session.status == SessionStatus.UPLOADING:
                stage = 'uploading'
            elif session.status == SessionStatus.PROCESSING:
                # Check if files are still processing
                pending_files = processing_summary.get('by_status', {}).get('PENDING', 0)
                processing_files = processing_summary.get('by_status', {}).get('PROCESSING', 0)
                
                if pending_files > 0 or processing_files > 0:
                    stage = 'processing_files'
                else:
                    stage = 'validating'
            elif session.status == SessionStatus.COMPLETED:
                stage = 'completed'
            elif session.status == SessionStatus.FAILED:
                stage = 'failed'
            else:
                stage = 'unknown'
            
            return {
                'session_id': str(session_id),
                'session_status': session.status.value,
                'overall_result': session.overall_result.value if session.overall_result else None,
                'workflow_stage': stage,
                'created_at': session.created_at.isoformat(),
                'updated_at': session.updated_at.isoformat(),
                'processing_summary': processing_summary,
                'validation_summary': validation_summary.dict() if validation_summary else None
            }
            
        except Exception as e:
            self.logger.error(f'Failed to get workflow status for session {session_id}: {str(e)}')
            return {
                'error': str(e)
            }
    
    def retry_failed_processing(self, session_id: UUID, db: Session) -> Dict[str, Any]:
        """Retry processing for failed files in a session"""
        try:
            self.logger.info(f'Retrying failed processing for session: {session_id}')
            
            # Process files again (will only process PENDING and FAILED files)
            result = self.file_processor.process_session_files(str(session_id), db)
            
            # If all files are now successful, trigger validation
            if result['success'] and result['failed_count'] == 0:
                self.logger.info(f'All files processed successfully, triggering validation for session {session_id}')
                validation_result = self.validator.validate_session(session_id, db)
                
                return {
                    'success': True,
                    'processing_result': result,
                    'validation_result': validation_result
                }
            
            return {
                'success': result['success'],
                'processing_result': result
            }
            
        except Exception as e:
            self.logger.error(f'Failed to retry processing for session {session_id}: {str(e)}')
            return {
                'success': False,
                'error': str(e)
            }
