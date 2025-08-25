import re
from typing import List, Optional, Dict, Any


# Regex patterns for extracting QC data
PATTERNS = {
    # Board serials: VGN-XXXXX-XXXX (may be missing VGN- prefix)
    'board_serial': r'(?:VGN[-_]?)?(\d{5}[-_]\d{4})',
    'board_serial_full': r'VGN[-_]?(\d{5}[-_]\d{4})',
    
    # Board part numbers: PCA-XXXX-YY
    'board_part_number': r'PCA[-_](\d{4})[-_]([A-Z]\d?)',
    
    # Unit serial: INF-XXXX (may be missing INF- prefix)
    'unit_serial': r'(?:INF[-_]?)?(\d{4})',
    'unit_serial_full': r'INF[-_]?(\d{4})',
    
    # Job number: 5 digits
    'job_number': r'\b(\d{5})\b',
    
    # Work instruction: DRW-XXXX-YY
    'work_instruction': r'DRW[-_](\d{4})[-_]([A-Z]\d?)',
    
    # Flight status
    'flight_status': r'\b(FLIGHT|EDU\s*[-–]?\s*NOT\s+FOR\s+FLIGHT)\b',
    
    # Revision patterns
    'revision': r'\bRev\s*([A-Z]\d?)\b',
    'revision_column': r'\b([A-Z]\d?)\b',  # For BOM column parsing
    
    # Part numbers (general)
    'part_number': r'\b([A-Z]{2,4}[-_]\d{4}[-_][A-Z]\d?)\b'
}


def extract_board_serials(text: str) -> List[str]:
    """Extract board serial numbers, normalizing to VGN-XXXXX-XXXX format"""
    matches = re.findall(PATTERNS['board_serial'], text, re.IGNORECASE)
    serials = []
    
    for match in matches:
        # Normalize format
        serial = match.replace('_', '-')
        if not serial.startswith('VGN-'):
            serial = f'VGN-{serial}'
        serials.append(serial)
    
    return list(set(serials))  # Remove duplicates


def extract_unit_serials(text: str) -> List[str]:
    """Extract unit serial numbers, normalizing to INF-XXXX format"""
    matches = re.findall(PATTERNS['unit_serial'], text, re.IGNORECASE)
    serials = []
    
    for match in matches:
        # Normalize format
        if not match.startswith('INF-'):
            serial = f'INF-{match}'
        else:
            serial = match
        serials.append(serial)
    
    return list(set(serials))  # Remove duplicates


def extract_board_part_numbers(text: str) -> List[str]:
    """Extract board part numbers in PCA-XXXX-YY format"""
    matches = re.findall(PATTERNS['board_part_number'], text, re.IGNORECASE)
    part_numbers = []
    
    for match in matches:
        part_num = f'PCA-{match[0]}-{match[1].upper()}'
        part_numbers.append(part_num)
    
    return list(set(part_numbers))


def extract_work_instructions(text: str) -> List[str]:
    """Extract work instruction numbers in DRW-XXXX-YY format"""
    matches = re.findall(PATTERNS['work_instruction'], text, re.IGNORECASE)
    instructions = []
    
    for match in matches:
        instruction = f'DRW-{match[0]}-{match[1].upper()}'
        instructions.append(instruction)
    
    return list(set(instructions))


def extract_job_numbers(text: str) -> List[str]:
    """Extract 5-digit job numbers"""
    matches = re.findall(PATTERNS['job_number'], text)
    return list(set(matches))


def extract_flight_status(text: str) -> Optional[str]:
    """Extract flight status from text"""
    match = re.search(PATTERNS['flight_status'], text, re.IGNORECASE)
    if match:
        status = match.group(1).strip()
        # Normalize format
        if 'EDU' in status.upper():
            return 'EDU - NOT FOR FLIGHT'
        else:
            return 'FLIGHT'
    return None


def extract_revisions(text: str) -> List[str]:
    """Extract revision numbers"""
    matches = re.findall(PATTERNS['revision'], text, re.IGNORECASE)
    return [rev.upper() for rev in set(matches)]


def extract_seq_20_data(text: str) -> Dict[str, Any]:
    """Extract data from Seq 20 section of traveler documents"""
    # Look for Seq 20 section
    seq_20_pattern = r'(?:Seq\s*20|Sequence\s*20)(.*?)(?:Seq\s*\d+|$)'
    seq_20_match = re.search(seq_20_pattern, text, re.IGNORECASE | re.DOTALL)
    
    if not seq_20_match:
        return {}
    
    seq_20_text = seq_20_match.group(1)
    
    return {
        'unit_serials': extract_unit_serials(seq_20_text),
        'board_serials': extract_board_serials(seq_20_text),
        'part_numbers': extract_board_part_numbers(seq_20_text)
    }


def normalize_serial_number(serial: str, prefix: str) -> str:
    """Normalize serial number with proper prefix"""
    clean_serial = serial.strip().replace('_', '-')
    
    if not clean_serial.startswith(prefix + '-'):
        # Extract just the number part
        number_part = re.sub(r'^[A-Z]*[-_]?', '', clean_serial)
        return f'{prefix}-{number_part}'
    
    return clean_serial


def clean_text_for_extraction(text: str) -> str:
    """Clean text to improve extraction accuracy"""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Normalize common separators
    text = text.replace('_', '-')
    
    # Remove common OCR artifacts
    text = re.sub(r'[^\w\s\-.,:]', ' ', text)
    
    return text.strip()


def extract_all_data(text: str) -> Dict[str, Any]:
    """Extract all relevant data from text"""
    clean_text = clean_text_for_extraction(text)
    
    return {
        'board_serials': extract_board_serials(clean_text),
        'unit_serials': extract_unit_serials(clean_text),
        'board_part_numbers': extract_board_part_numbers(clean_text),
        'work_instructions': extract_work_instructions(clean_text),
        'job_numbers': extract_job_numbers(clean_text),
        'flight_status': extract_flight_status(clean_text),
        'revisions': extract_revisions(clean_text),
        'seq_20_data': extract_seq_20_data(clean_text),
        'raw_text': text  # Keep original for debugging
    }
