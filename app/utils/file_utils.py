import os
import magic
from pathlib import Path
from typing import Optional


def get_file_mime_type(file_path: str) -> str:
    """Get MIME type of a file using python-magic"""
    try:
        mime = magic.Magic(mime=True)
        return mime.from_file(file_path)
    except Exception:
        # Fallback to basic extension-based detection
        return get_mime_type_from_extension(file_path)


def get_mime_type_from_extension(file_path: str) -> str:
    """Get MIME type based on file extension (fallback)"""
    extension = Path(file_path).suffix.lower()
    
    mime_map = {
        '.pdf': 'application/pdf',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.xls': 'application/vnd.ms-excel'
    }
    
    return mime_map.get(extension, 'application/octet-stream')


def ensure_directory_exists(directory_path: str) -> bool:
    """Ensure a directory exists, create if it doesn't"""
    try:
        Path(directory_path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception:
        return False


def get_file_size(file_path: str) -> Optional[int]:
    """Get file size in bytes"""
    try:
        return os.path.getsize(file_path)
    except Exception:
        return None


def is_safe_filename(filename: str) -> bool:
    """Check if filename is safe (no path traversal)"""
    # Remove any path components
    safe_name = os.path.basename(filename)
    
    # Check for dangerous patterns
    dangerous_patterns = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
    
    for pattern in dangerous_patterns:
        if pattern in safe_name:
            return False
    
    return len(safe_name) > 0 and len(safe_name) <= 255


def clean_filename(filename: str) -> str:
    """Clean filename to make it safe for storage"""
    # Get just the basename
    clean_name = os.path.basename(filename)
    
    # Replace dangerous characters
    dangerous_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for char in dangerous_chars:
        clean_name = clean_name.replace(char, '_')
    
    # Limit length
    if len(clean_name) > 255:
        name_part, ext = os.path.splitext(clean_name)
        clean_name = name_part[:255-len(ext)] + ext
    
    return clean_name
