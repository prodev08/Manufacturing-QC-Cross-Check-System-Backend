import re
from typing import List, Set, Dict, Any, Optional
from difflib import SequenceMatcher


def normalize_serial_number(serial: str, prefix: str) -> str:
    """Normalize serial number with proper prefix"""
    if not serial:
        return ""
    
    # Clean the serial
    clean_serial = serial.strip().upper().replace('_', '-')
    
    # If it already has the correct prefix, return as-is
    if clean_serial.startswith(f'{prefix}-'):
        return clean_serial
    
    # Remove any existing prefix and add the correct one
    # Extract just the number part (digits and hyphens)
    number_match = re.search(r'(\d+[-_]?\d*)', clean_serial)
    if number_match:
        number_part = number_match.group(1).replace('_', '-')
        return f'{prefix}-{number_part}'
    
    return clean_serial


def normalize_board_serial(serial: str) -> str:
    """Normalize board serial to VGN-XXXXX-XXXX format"""
    return normalize_serial_number(serial, 'VGN')


def normalize_unit_serial(serial: str) -> str:
    """Normalize unit serial to INF-XXXX format"""
    return normalize_serial_number(serial, 'INF')


def normalize_part_number(part_number: str) -> str:
    """Normalize part number format"""
    if not part_number:
        return ""
    
    # Clean and uppercase
    clean_part = part_number.strip().upper().replace('_', '-')
    
    # Handle common patterns like PCA-XXXX-YY, DRW-XXXX-YY
    part_match = re.match(r'([A-Z]+)[-_]?(\d+)[-_]?([A-Z]\d?)', clean_part)
    if part_match:
        prefix, number, suffix = part_match.groups()
        return f'{prefix}-{number}-{suffix}'
    
    return clean_part


def normalize_revision(revision: str) -> str:
    """Normalize revision format"""
    if not revision:
        return ""
    
    # Clean revision
    clean_rev = revision.strip().upper()
    
    # Remove 'REV' prefix if present
    clean_rev = re.sub(r'^REV\s*', '', clean_rev)
    
    return clean_rev


def normalize_job_number(job_number: str) -> str:
    """Normalize job number to 5-digit format"""
    if not job_number:
        return ""
    
    # Extract digits
    digits = re.sub(r'\D', '', job_number)
    
    # Ensure it's 5 digits
    if len(digits) == 5:
        return digits
    
    return job_number.strip()


def normalize_flight_status(status: str) -> str:
    """Normalize flight status"""
    if not status:
        return ""
    
    clean_status = status.strip().upper()
    
    if 'EDU' in clean_status or 'NOT FOR FLIGHT' in clean_status:
        return 'EDU - NOT FOR FLIGHT'
    elif 'FLIGHT' in clean_status:
        return 'FLIGHT'
    
    return clean_status


def find_best_matches(items1: List[str], items2: List[str], threshold: float = 0.8) -> List[tuple]:
    """Find best string matches between two lists using fuzzy matching"""
    matches = []
    
    for item1 in items1:
        best_match = None
        best_ratio = 0
        
        for item2 in items2:
            ratio = SequenceMatcher(None, item1.lower(), item2.lower()).ratio()
            if ratio > best_ratio and ratio >= threshold:
                best_ratio = ratio
                best_match = item2
        
        if best_match:
            matches.append((item1, best_match, best_ratio))
    
    return matches


def compare_normalized_lists(list1: List[str], list2: List[str], normalizer_func=None) -> Dict[str, Any]:
    """Compare two lists with optional normalization"""
    if normalizer_func:
        norm_list1 = [normalizer_func(item) for item in list1]
        norm_list2 = [normalizer_func(item) for item in list2]
    else:
        norm_list1 = list1
        norm_list2 = list2
    
    set1 = set(norm_list1)
    set2 = set(norm_list2)
    
    matches = set1.intersection(set2)
    missing_in_2 = set1 - set2
    missing_in_1 = set2 - set1
    
    return {
        'matches': list(matches),
        'missing_in_second': list(missing_in_2),
        'missing_in_first': list(missing_in_1),
        'match_count': len(matches),
        'total_unique_first': len(set1),
        'total_unique_second': len(set2),
        'match_percentage': (len(matches) / max(len(set1), len(set2)) * 100) if (set1 or set2) else 100
    }


def extract_data_by_file_type(file_data: Dict[str, Any]) -> Dict[str, List[str]]:
    """Extract relevant data fields based on file type"""
    file_type = file_data.get('file_type', '')
    
    result = {
        'job_numbers': [],
        'part_numbers': [],
        'board_serials': [],
        'unit_serials': [],
        'revisions': [],
        'work_instructions': [],
        'flight_status': None
    }
    
    if file_type == 'TRAVELER_PDF':
        result.update({
            'job_numbers': file_data.get('job_numbers', []),
            'part_numbers': file_data.get('board_part_numbers', []) + file_data.get('work_instructions', []),
            'board_serials': file_data.get('board_serials', []),
            'unit_serials': file_data.get('unit_serials', []),
            'revisions': file_data.get('revisions', []),
            'work_instructions': file_data.get('work_instructions', []),
            'seq_20_data': file_data.get('seq_20_data', {})
        })
    
    elif file_type == 'PRODUCT_IMAGE':
        result.update({
            'board_serials': file_data.get('board_serials', []),
            'unit_serials': file_data.get('unit_serials', []),
            'part_numbers': file_data.get('board_part_numbers', []),
            'flight_status': file_data.get('flight_status')
        })
    
    elif file_type == 'BOM_EXCEL':
        result.update({
            'job_numbers': file_data.get('job_numbers', []),
            'part_numbers': file_data.get('part_numbers', []),
            'revisions': file_data.get('revisions', [])
        })
    
    return result


def get_normalization_info(original: str, normalized: str) -> Dict[str, str]:
    """Get information about what normalization was applied"""
    if original == normalized:
        return {'type': 'none', 'description': 'No normalization needed'}
    
    changes = []
    
    if original.lower() != normalized.lower():
        changes.append('case conversion')
    
    if '_' in original and '-' in normalized:
        changes.append('underscore to hyphen')
    
    if not original.startswith(('VGN-', 'INF-')) and normalized.startswith(('VGN-', 'INF-')):
        changes.append('prefix added')
    
    return {
        'type': 'applied',
        'description': f'Applied: {", ".join(changes)}' if changes else 'Format standardized'
    }
