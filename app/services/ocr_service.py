import logging
import cv2
import numpy as np
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract

from app.utils.patterns import extract_all_data

logger = logging.getLogger(__name__)


class OCRService:
    """Service for OCR processing of product images"""
    
    def __init__(self):
        self.logger = logger
        # Configure Tesseract (you may need to set the path on Windows)
        # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    
    def preprocess_image(self, image_path: str) -> Image.Image:
        """Preprocess image to improve OCR accuracy"""
        try:
            # Open image with PIL
            image = Image.open(image_path)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)
            
            # Enhance sharpness
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(2.0)
            
            # Convert to grayscale
            image = image.convert('L')
            
            # Apply slight blur to reduce noise
            image = image.filter(ImageFilter.MedianFilter(size=3))
            
            return image
            
        except Exception as e:
            self.logger.error(f'Image preprocessing failed for {image_path}: {str(e)}')
            # Return original image if preprocessing fails
            return Image.open(image_path)
    
    def preprocess_with_opencv(self, image_path: str) -> np.ndarray:
        """Advanced preprocessing using OpenCV"""
        try:
            # Read image
            image = cv2.imread(image_path)
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Apply adaptive threshold
            thresh = cv2.adaptiveThreshold(
                blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            # Morphological operations to clean up
            kernel = np.ones((2, 2), np.uint8)
            cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            
            return cleaned
            
        except Exception as e:
            self.logger.error(f'OpenCV preprocessing failed for {image_path}: {str(e)}')
            # Fallback to simple grayscale
            image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            return image
    
    def extract_text_basic(self, image_path: str) -> str:
        """Extract text using basic Tesseract OCR"""
        try:
            # Preprocess image
            image = self.preprocess_image(image_path)
            
            # Configure Tesseract
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_'
            
            # Extract text
            text = pytesseract.image_to_string(image, config=custom_config)
            
            return text.strip()
            
        except Exception as e:
            self.logger.error(f'Basic OCR failed for {image_path}: {str(e)}')
            return ''
    
    def extract_text_advanced(self, image_path: str) -> str:
        """Extract text using advanced preprocessing"""
        try:
            # Preprocess with OpenCV
            processed_image = self.preprocess_with_opencv(image_path)
            
            # Configure Tesseract for better accuracy
            custom_config = r'--oem 3 --psm 6'
            
            # Extract text
            text = pytesseract.image_to_string(processed_image, config=custom_config)
            
            return text.strip()
            
        except Exception as e:
            self.logger.error(f'Advanced OCR failed for {image_path}: {str(e)}')
            return ''
    
    def extract_text_multiple_configs(self, image_path: str) -> str:
        """Try multiple OCR configurations and return the best result"""
        configs = [
            r'--oem 3 --psm 6',  # Standard
            r'--oem 3 --psm 8',  # Single word
            r'--oem 3 --psm 7',  # Single text line
            r'--oem 3 --psm 11', # Sparse text
            r'--oem 3 --psm 13'  # Raw line
        ]
        
        best_text = ''
        best_confidence = 0
        
        try:
            image = self.preprocess_image(image_path)
            
            for config in configs:
                try:
                    # Get text and confidence
                    data = pytesseract.image_to_data(image, config=config, output_type=pytesseract.Output.DICT)
                    
                    # Calculate average confidence
                    confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                    
                    # Get text
                    text = pytesseract.image_to_string(image, config=config).strip()
                    
                    if avg_confidence > best_confidence and text:
                        best_confidence = avg_confidence
                        best_text = text
                        
                except Exception as e:
                    self.logger.debug(f'OCR config {config} failed: {str(e)}')
                    continue
            
            return best_text
            
        except Exception as e:
            self.logger.error(f'Multiple config OCR failed for {image_path}: {str(e)}')
            return ''
    
    def extract_text(self, image_path: str) -> str:
        """Extract text using the best available method"""
        # Try advanced method first
        text = self.extract_text_advanced(image_path)
        
        # Fallback to multiple configs if advanced fails
        if not text or len(text) < 10:
            self.logger.warning(f'Advanced OCR gave poor results for {image_path}, trying multiple configs')
            text = self.extract_text_multiple_configs(image_path)
        
        # Final fallback to basic method
        if not text:
            self.logger.warning(f'Multiple configs failed for {image_path}, trying basic OCR')
            text = self.extract_text_basic(image_path)
        
        return text
    
    def extract_product_image_data(self, file_path: str) -> Dict[str, Any]:
        """Extract structured data from a product image"""
        try:
            # Extract raw text
            raw_text = self.extract_text(file_path)
            
            if not raw_text:
                return {
                    'success': False,
                    'error': 'No text extracted from image',
                    'raw_text': ''
                }
            
            # Extract structured data using patterns
            extracted_data = extract_all_data(raw_text)
            
            # Add image-specific processing
            result = {
                'success': True,
                'file_type': 'PRODUCT_IMAGE',
                'extraction_method': 'tesseract_ocr',
                'image_info': self._get_image_info(file_path),
                **extracted_data
            }
            
            self.logger.info(f'Successfully extracted data from image: {file_path}')
            return result
            
        except Exception as e:
            self.logger.error(f'Image data extraction failed for {file_path}: {str(e)}')
            return {
                'success': False,
                'error': str(e),
                'file_type': 'PRODUCT_IMAGE'
            }
    
    def _get_image_info(self, image_path: str) -> Dict[str, Any]:
        """Get basic image information"""
        try:
            with Image.open(image_path) as img:
                return {
                    'width': img.width,
                    'height': img.height,
                    'mode': img.mode,
                    'format': img.format
                }
        except Exception:
            return {}
    
    def validate_image(self, file_path: str) -> Dict[str, Any]:
        """Validate that the image is readable and suitable for OCR"""
        if not Path(file_path).exists():
            return {
                'valid': False,
                'error': 'File does not exist'
            }
        
        try:
            with Image.open(file_path) as img:
                # Check image properties
                width, height = img.size
                
                if width < 100 or height < 100:
                    return {
                        'valid': False,
                        'error': 'Image too small for reliable OCR'
                    }
                
                # Try a quick OCR test
                test_text = pytesseract.image_to_string(img)
                
                return {
                    'valid': True,
                    'width': width,
                    'height': height,
                    'mode': img.mode,
                    'format': img.format,
                    'has_text': bool(test_text.strip()),
                    'text_preview': test_text[:100] if test_text else ''
                }
                
        except Exception as e:
            return {
                'valid': False,
                'error': f'Image validation failed: {str(e)}'
            }
