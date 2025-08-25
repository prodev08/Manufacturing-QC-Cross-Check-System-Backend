import logging
from typing import Dict, Any, Optional
from pathlib import Path
import PyPDF2
import pdfplumber

from app.utils.patterns import extract_all_data

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Service for extracting text and data from PDF documents"""
    
    def __init__(self):
        self.logger = logger
    
    def extract_text_pypdf2(self, file_path: str) -> str:
        """Extract text using PyPDF2"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ''
                
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text() + '\n'
                
                return text.strip()
                
        except Exception as e:
            self.logger.error(f'PyPDF2 extraction failed for {file_path}: {str(e)}')
            return ''
    
    def extract_text_pdfplumber(self, file_path: str) -> str:
        """Extract text using pdfplumber (more accurate for complex layouts)"""
        try:
            with pdfplumber.open(file_path) as pdf:
                text = ''
                
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + '\n'
                
                return text.strip()
                
        except Exception as e:
            self.logger.error(f'pdfplumber extraction failed for {file_path}: {str(e)}')
            return ''
    
    def extract_text(self, file_path: str) -> str:
        """Extract text using the best available method"""
        # Try pdfplumber first (more accurate)
        text = self.extract_text_pdfplumber(file_path)
        
        # Fallback to PyPDF2 if pdfplumber fails
        if not text:
            self.logger.warning(f'pdfplumber failed for {file_path}, trying PyPDF2')
            text = self.extract_text_pypdf2(file_path)
        
        return text
    
    def extract_traveler_data(self, file_path: str) -> Dict[str, Any]:
        """Extract structured data from a Traveler PDF document"""
        try:
            # Extract raw text
            raw_text = self.extract_text(file_path)
            
            if not raw_text:
                return {
                    'success': False,
                    'error': 'No text extracted from PDF',
                    'raw_text': ''
                }
            
            # Extract structured data using patterns
            extracted_data = extract_all_data(raw_text)
            
            # Add PDF-specific processing
            result = {
                'success': True,
                'file_type': 'TRAVELER_PDF',
                'extraction_method': 'pdfplumber+pypdf2',
                'page_count': self._get_page_count(file_path),
                **extracted_data
            }
            
            self.logger.info(f'Successfully extracted data from PDF: {file_path}')
            return result
            
        except Exception as e:
            self.logger.error(f'PDF data extraction failed for {file_path}: {str(e)}')
            return {
                'success': False,
                'error': str(e),
                'file_type': 'TRAVELER_PDF'
            }
    
    def _get_page_count(self, file_path: str) -> int:
        """Get the number of pages in the PDF"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                return len(pdf_reader.pages)
        except Exception:
            return 0
    
    def validate_pdf(self, file_path: str) -> Dict[str, Any]:
        """Validate that the PDF is readable and contains text"""
        if not Path(file_path).exists():
            return {
                'valid': False,
                'error': 'File does not exist'
            }
        
        try:
            # Check if file can be opened
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                page_count = len(pdf_reader.pages)
                
                if page_count == 0:
                    return {
                        'valid': False,
                        'error': 'PDF contains no pages'
                    }
                
                # Try to extract text from first page
                first_page_text = pdf_reader.pages[0].extract_text()
                
                return {
                    'valid': True,
                    'page_count': page_count,
                    'has_text': bool(first_page_text.strip()),
                    'first_page_preview': first_page_text[:200] if first_page_text else ''
                }
                
        except Exception as e:
            return {
                'valid': False,
                'error': f'PDF validation failed: {str(e)}'
            }
