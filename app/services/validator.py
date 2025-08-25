import logging
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from uuid import UUID

from app.models.session import Session as SessionModel, OverallResult
from app.models.file import UploadedFile, FileType
from app.models.validation import ValidationResult, ValidationStatus, CheckType
from app.utils.normalizers import (
    normalize_board_serial, normalize_unit_serial, normalize_part_number,
    normalize_revision, normalize_job_number, normalize_flight_status,
    compare_normalized_lists, extract_data_by_file_type, get_normalization_info
)

logger = logging.getLogger(__name__)


class QCValidator:
    """Service for cross-validating QC data across multiple files"""
    
    def __init__(self):
        self.logger = logger
    
    def validate_session(self, session_id: UUID, db: Session) -> Dict[str, Any]:
        """Perform comprehensive validation for a session"""
        try:
            self.logger.info(f'Starting validation for session: {session_id}')
            
            # Get session and files
            session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
            if not session:
                raise ValueError(f'Session {session_id} not found')
            
            files = db.query(UploadedFile).filter(
                UploadedFile.session_id == session_id,
                UploadedFile.extracted_data.isnot(None)
            ).all()
            
            if not files:
                return {
                    'success': False,
                    'error': 'No processed files found for validation'
                }
            
            # Extract data by file type
            file_data = self._extract_session_data(files)
            
            # Perform validation checks
            validation_results = []
            
            # 1. Job number validation (highest priority)
            job_result = self._validate_job_numbers(file_data, session_id)
            validation_results.extend(job_result)
            
            # 2. Part number validation
            part_result = self._validate_part_numbers(file_data, session_id)
            validation_results.extend(part_result)
            
            # 3. Revision validation
            revision_result = self._validate_revisions(file_data, session_id)
            validation_results.extend(revision_result)
            
            # 4. Board serial validation
            board_serial_result = self._validate_board_serials(file_data, session_id)
            validation_results.extend(board_serial_result)
            
            # 5. Unit serial validation
            unit_serial_result = self._validate_unit_serials(file_data, session_id)
            validation_results.extend(unit_serial_result)
            
            # 6. Flight status validation
            flight_result = self._validate_flight_status(file_data, session_id)
            validation_results.extend(flight_result)
            
            # 7. File completeness check
            completeness_result = self._validate_file_completeness(file_data, session_id)
            validation_results.extend(completeness_result)
            
            # Save validation results to database
            for result_data in validation_results:
                validation_result = ValidationResult(**result_data)
                db.add(validation_result)
            
            # Determine overall result
            overall_result = self._determine_overall_result(validation_results)
            session.overall_result = overall_result
            
            db.commit()
            
            return {
                'success': True,
                'session_id': str(session_id),
                'overall_result': overall_result.value,
                'validation_count': len(validation_results),
                'results': validation_results
            }
            
        except Exception as e:
            self.logger.error(f'Validation failed for session {session_id}: {str(e)}')
            db.rollback()
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_session_data(self, files: List[UploadedFile]) -> Dict[str, Any]:
        """Extract and organize data from all files in the session"""
        session_data = {
            'traveler_data': None,
            'image_data': None,
            'bom_data': [],
            'file_info': {}
        }
        
        for file in files:
            extracted_data = file.extracted_data
            if not extracted_data or not extracted_data.get('success'):
                continue
            
            file_type = file.file_type
            processed_data = extract_data_by_file_type(extracted_data)
            
            session_data['file_info'][str(file.id)] = {
                'filename': file.filename,
                'file_type': file_type.value,
                'data': processed_data
            }
            
            if file_type == FileType.TRAVELER_PDF:
                session_data['traveler_data'] = processed_data
            elif file_type == FileType.PRODUCT_IMAGE:
                session_data['image_data'] = processed_data
            elif file_type == FileType.BOM_EXCEL:
                session_data['bom_data'].append(processed_data)
        
        return session_data
    
    def _validate_job_numbers(self, file_data: Dict[str, Any], session_id: UUID) -> List[Dict[str, Any]]:
        """Validate job numbers between Traveler and BOM files"""
        results = []
        
        traveler_data = file_data.get('traveler_data')
        bom_data_list = file_data.get('bom_data', [])
        
        if not traveler_data or not bom_data_list:
            results.append({
                'session_id': session_id,
                'check_type': CheckType.JOB_NUMBER,
                'status': ValidationStatus.FAIL,
                'description': 'Missing required files for job number validation',
                'details': 'Need both Traveler PDF and BOM Excel files'
            })
            return results
        
        traveler_jobs = [normalize_job_number(job) for job in traveler_data.get('job_numbers', [])]
        
        for bom_data in bom_data_list:
            bom_jobs = [normalize_job_number(job) for job in bom_data.get('job_numbers', [])]
            
            comparison = compare_normalized_lists(traveler_jobs, bom_jobs)
            
            if comparison['matches']:
                results.append({
                    'session_id': session_id,
                    'check_type': CheckType.JOB_NUMBER,
                    'status': ValidationStatus.PASS,
                    'description': f'Job numbers match: {", ".join(comparison["matches"])}',
                    'expected_value': ', '.join(traveler_jobs),
                    'actual_value': ', '.join(bom_jobs)
                })
            else:
                results.append({
                    'session_id': session_id,
                    'check_type': CheckType.JOB_NUMBER,
                    'status': ValidationStatus.FAIL,
                    'description': 'Job number mismatch between Traveler and BOM',
                    'expected_value': ', '.join(traveler_jobs),
                    'actual_value': ', '.join(bom_jobs),
                    'details': f'Traveler missing: {comparison["missing_in_first"]}, BOM missing: {comparison["missing_in_second"]}'
                })
        
        return results
    
    def _validate_part_numbers(self, file_data: Dict[str, Any], session_id: UUID) -> List[Dict[str, Any]]:
        """Validate part numbers across Traveler, Image, and BOM files"""
        results = []
        
        traveler_data = file_data.get('traveler_data')
        bom_data_list = file_data.get('bom_data', [])
        
        if not traveler_data or not bom_data_list:
            return results
        
        traveler_parts = [normalize_part_number(part) for part in traveler_data.get('part_numbers', [])]
        
        for bom_data in bom_data_list:
            bom_parts = [normalize_part_number(part) for part in bom_data.get('part_numbers', [])]
            
            comparison = compare_normalized_lists(traveler_parts, bom_parts)
            
            # Check for critical mismatches (parts in Traveler but not in BOM)
            if comparison['missing_in_second']:
                results.append({
                    'session_id': session_id,
                    'check_type': CheckType.PART_NUMBER,
                    'status': ValidationStatus.FAIL,
                    'description': f'Part numbers found in Traveler but missing in BOM: {", ".join(comparison["missing_in_second"])}',
                    'expected_value': ', '.join(traveler_parts),
                    'actual_value': ', '.join(bom_parts)
                })
            elif comparison['missing_in_first']:
                results.append({
                    'session_id': session_id,
                    'check_type': CheckType.PART_NUMBER,
                    'status': ValidationStatus.WARNING,
                    'description': f'Part numbers in BOM but not in Traveler: {", ".join(comparison["missing_in_first"])}',
                    'expected_value': ', '.join(traveler_parts),
                    'actual_value': ', '.join(bom_parts)
                })
            else:
                results.append({
                    'session_id': session_id,
                    'check_type': CheckType.PART_NUMBER,
                    'status': ValidationStatus.PASS,
                    'description': f'Part numbers match: {", ".join(comparison["matches"])}',
                    'expected_value': ', '.join(traveler_parts),
                    'actual_value': ', '.join(bom_parts)
                })
        
        return results
    
    def _validate_revisions(self, file_data: Dict[str, Any], session_id: UUID) -> List[Dict[str, Any]]:
        """Validate revision numbers across all sources"""
        results = []
        
        traveler_data = file_data.get('traveler_data')
        bom_data_list = file_data.get('bom_data', [])
        
        if not traveler_data or not bom_data_list:
            return results
        
        traveler_revisions = [normalize_revision(rev) for rev in traveler_data.get('revisions', [])]
        
        for bom_data in bom_data_list:
            bom_revisions = [normalize_revision(rev) for rev in bom_data.get('revisions', [])]
            
            # Check for revision mismatches (like Rev F2 vs Rev F)
            for t_rev in traveler_revisions:
                matching_bom_revs = [b_rev for b_rev in bom_revisions if b_rev.startswith(t_rev[0]) if t_rev]
                
                if not matching_bom_revs:
                    results.append({
                        'session_id': session_id,
                        'check_type': CheckType.REVISION,
                        'status': ValidationStatus.FAIL,
                        'description': f'Revision {t_rev} from Traveler not found in BOM',
                        'expected_value': t_rev,
                        'actual_value': ', '.join(bom_revisions)
                    })
                elif t_rev not in matching_bom_revs:
                    # Minor revision difference (e.g., F vs F2)
                    results.append({
                        'session_id': session_id,
                        'check_type': CheckType.REVISION,
                        'status': ValidationStatus.WARNING,
                        'description': f'Revision format difference: Traveler has {t_rev}, BOM has {matching_bom_revs[0]}',
                        'expected_value': t_rev,
                        'actual_value': matching_bom_revs[0]
                    })
                else:
                    results.append({
                        'session_id': session_id,
                        'check_type': CheckType.REVISION,
                        'status': ValidationStatus.PASS,
                        'description': f'Revision {t_rev} matches across sources',
                        'expected_value': t_rev,
                        'actual_value': t_rev
                    })
        
        return results
    
    def _validate_board_serials(self, file_data: Dict[str, Any], session_id: UUID) -> List[Dict[str, Any]]:
        """Validate board serials between Traveler and Image"""
        results = []
        
        traveler_data = file_data.get('traveler_data')
        image_data = file_data.get('image_data')
        
        if not traveler_data or not image_data:
            results.append({
                'session_id': session_id,
                'check_type': CheckType.BOARD_SERIAL,
                'status': ValidationStatus.WARNING,
                'description': 'Cannot validate board serials - missing Traveler or Image data'
            })
            return results
        
        # Get Seq 20 data from traveler if available
        seq_20_data = traveler_data.get('seq_20_data', {})
        traveler_serials = seq_20_data.get('board_serials', []) or traveler_data.get('board_serials', [])
        image_serials = image_data.get('board_serials', [])
        
        # Normalize serials
        norm_traveler = [normalize_board_serial(serial) for serial in traveler_serials]
        norm_image = [normalize_board_serial(serial) for serial in image_serials]
        
        comparison = compare_normalized_lists(norm_traveler, norm_image)
        
        if comparison['matches']:
            results.append({
                'session_id': session_id,
                'check_type': CheckType.BOARD_SERIAL,
                'status': ValidationStatus.PASS,
                'description': f'Board serials match: {", ".join(comparison["matches"])}',
                'expected_value': ', '.join(norm_traveler),
                'actual_value': ', '.join(norm_image),
                'details': 'Normalized VGN- prefix handling applied'
            })
        else:
            results.append({
                'session_id': session_id,
                'check_type': CheckType.BOARD_SERIAL,
                'status': ValidationStatus.FAIL,
                'description': 'Board serial mismatch between Traveler Seq 20 and Image',
                'expected_value': ', '.join(norm_traveler),
                'actual_value': ', '.join(norm_image)
            })
        
        return results
    
    def _validate_unit_serials(self, file_data: Dict[str, Any], session_id: UUID) -> List[Dict[str, Any]]:
        """Validate unit serials between Traveler and Image"""
        results = []
        
        traveler_data = file_data.get('traveler_data')
        image_data = file_data.get('image_data')
        
        if not traveler_data or not image_data:
            results.append({
                'session_id': session_id,
                'check_type': CheckType.UNIT_SERIAL,
                'status': ValidationStatus.WARNING,
                'description': 'Cannot validate unit serials - missing Traveler or Image data'
            })
            return results
        
        # Get Seq 20 data from traveler if available
        seq_20_data = traveler_data.get('seq_20_data', {})
        traveler_serials = seq_20_data.get('unit_serials', []) or traveler_data.get('unit_serials', [])
        image_serials = image_data.get('unit_serials', [])
        
        # Normalize serials
        norm_traveler = [normalize_unit_serial(serial) for serial in traveler_serials]
        norm_image = [normalize_unit_serial(serial) for serial in image_serials]
        
        comparison = compare_normalized_lists(norm_traveler, norm_image)
        
        if comparison['matches']:
            results.append({
                'session_id': session_id,
                'check_type': CheckType.UNIT_SERIAL,
                'status': ValidationStatus.PASS,
                'description': f'Unit serials match: {", ".join(comparison["matches"])}',
                'expected_value': ', '.join(norm_traveler),
                'actual_value': ', '.join(norm_image),
                'details': 'Normalized INF- prefix handling applied'
            })
        else:
            results.append({
                'session_id': session_id,
                'check_type': CheckType.UNIT_SERIAL,
                'status': ValidationStatus.FAIL,
                'description': 'Unit serial mismatch between Traveler Seq 20 and Image',
                'expected_value': ', '.join(norm_traveler),
                'actual_value': ', '.join(norm_image)
            })
        
        return results
    
    def _validate_flight_status(self, file_data: Dict[str, Any], session_id: UUID) -> List[Dict[str, Any]]:
        """Validate flight status marking on image"""
        results = []
        
        image_data = file_data.get('image_data')
        
        if not image_data:
            results.append({
                'session_id': session_id,
                'check_type': CheckType.FLIGHT_STATUS,
                'status': ValidationStatus.WARNING,
                'description': 'Cannot validate flight status - no image data available'
            })
            return results
        
        flight_status = image_data.get('flight_status')
        
        if flight_status:
            normalized_status = normalize_flight_status(flight_status)
            results.append({
                'session_id': session_id,
                'check_type': CheckType.FLIGHT_STATUS,
                'status': ValidationStatus.PASS,
                'description': f'Flight status confirmed: {normalized_status}',
                'actual_value': normalized_status
            })
        else:
            results.append({
                'session_id': session_id,
                'check_type': CheckType.FLIGHT_STATUS,
                'status': ValidationStatus.WARNING,
                'description': 'Flight status marking not clearly detected on image'
            })
        
        return results
    
    def _validate_file_completeness(self, file_data: Dict[str, Any], session_id: UUID) -> List[Dict[str, Any]]:
        """Validate that all required files are present and readable"""
        results = []
        
        has_traveler = file_data.get('traveler_data') is not None
        has_image = file_data.get('image_data') is not None
        has_bom = len(file_data.get('bom_data', [])) > 0
        
        file_types_present = []
        if has_traveler:
            file_types_present.append('Traveler PDF')
        if has_image:
            file_types_present.append('Product Image')
        if has_bom:
            file_types_present.append('BOM Excel')
        
        missing_types = []
        if not has_traveler:
            missing_types.append('Traveler PDF')
        if not has_image:
            missing_types.append('Product Image')
        if not has_bom:
            missing_types.append('BOM Excel')
        
        if missing_types:
            results.append({
                'session_id': session_id,
                'check_type': CheckType.FILE_COMPLETENESS,
                'status': ValidationStatus.WARNING,
                'description': f'Missing file types: {", ".join(missing_types)}',
                'details': f'Present: {", ".join(file_types_present)}'
            })
        else:
            results.append({
                'session_id': session_id,
                'check_type': CheckType.FILE_COMPLETENESS,
                'status': ValidationStatus.PASS,
                'description': 'All required file types present and processed successfully'
            })
        
        return results
    
    def _determine_overall_result(self, validation_results: List[Dict[str, Any]]) -> OverallResult:
        """Determine overall validation result based on individual checks"""
        has_fail = any(result['status'] == ValidationStatus.FAIL for result in validation_results)
        has_warning = any(result['status'] == ValidationStatus.WARNING for result in validation_results)
        
        if has_fail:
            return OverallResult.FAIL
        elif has_warning:
            return OverallResult.WARNING
        else:
            return OverallResult.PASS
