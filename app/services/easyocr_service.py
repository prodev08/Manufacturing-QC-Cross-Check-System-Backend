import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor
import easyocr
from app.utils.patterns import extract_all_data

logger = logging.getLogger(__name__)


class EasyOCRService:
    """Service for image analysis using EasyOCR - optimized for manufacturing text"""
    
    def __init__(self):
        self.logger = logger
        self.reader = None
        # Thread pool for async processing
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="easyocr")
        
        try:
            # Initialize EasyOCR reader for English text
            self.reader = easyocr.Reader(['en'], gpu=False)  # Use CPU for stability
            self.logger.info("EasyOCR service initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize EasyOCR reader: {e}")
            self.reader = None
    
    def preprocess_image(self, image_path: str) -> np.ndarray:
        """Preprocess image for better OCR accuracy on manufacturing text"""
        try:
            # Read image
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"Could not read image: {image_path}")
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Apply different preprocessing techniques
            # 1. Gaussian blur to reduce noise
            blur = cv2.GaussianBlur(gray, (3, 3), 0)
            
            # 2. Adaptive thresholding for better contrast
            thresh = cv2.adaptiveThreshold(
                blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            # 3. Morphological operations to clean up text
            kernel = np.ones((2, 2), np.uint8)
            cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            
            return cleaned
            
        except Exception as e:
            self.logger.error(f"Image preprocessing failed for {image_path}: {e}")
            # Fallback to original image
            return cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    
    def create_rotated_versions(self, image) -> List[np.ndarray]:
        """Create rotated versions of the image to handle rotated text"""
        rotated_images = []
        
        # Original image
        rotated_images.append(image)
        
        # 90 degrees clockwise
        rotated_90 = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        rotated_images.append(rotated_90)
        
        # 90 degrees counterclockwise
        rotated_270 = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        rotated_images.append(rotated_270)
        
        # 180 degrees
        rotated_180 = cv2.rotate(image, cv2.ROTATE_180)
        rotated_images.append(rotated_180)
        
        return rotated_images
    
    def extract_text_with_confidence(self, image_path: str) -> List[Dict[str, Any]]:
        """Extract text with confidence scores using EasyOCR with rotation handling"""
        if not self.reader:
            self.logger.error("EasyOCR reader not available")
            return []
        
        try:
            all_results = []
            
            # 1. Direct OCR on original image
            original_results = self.reader.readtext(image_path, detail=1)
            all_results.extend([(bbox, text, conf, "original") for bbox, text, conf in original_results])
            
            # 2. OCR on preprocessed image
            try:
                preprocessed = self.preprocess_image(image_path)
                processed_results = self.reader.readtext(preprocessed, detail=1)
                all_results.extend([(bbox, text, conf, "preprocessed") for bbox, text, conf in processed_results])
            except Exception as e:
                self.logger.debug(f"Preprocessing failed: {e}")
            
            # 3. OCR on rotated images (for rotated text)
            try:
                # Get the original image
                original_image = cv2.imread(image_path)
                rotated_versions = self.create_rotated_versions(original_image)
                
                rotation_names = ["original", "90_cw", "90_ccw", "180"]
                
                for i, rotated_img in enumerate(rotated_versions[1:], 1):  # Skip original
                    try:
                        rotated_results = self.reader.readtext(rotated_img, detail=1)
                        all_results.extend([(bbox, text, conf, rotation_names[i]) for bbox, text, conf in rotated_results])
                    except Exception as e:
                        self.logger.debug(f"Rotation {rotation_names[i]} failed: {e}")
                        
            except Exception as e:
                self.logger.debug(f"Rotation processing failed: {e}")
            
            # 4. Filter and deduplicate results
            filtered_results = []
            seen_texts = set()
            
            for bbox, text, confidence, source in all_results:
                # Filter by confidence threshold
                if confidence > 0.25 and text.strip():  # Lower threshold for rotated text
                    # Clean the text
                    clean_text = text.strip().upper()
                    
                    # Skip very short text unless it looks like a serial/part number
                    if len(clean_text) < 3 and not re.match(r'^[A-Z0-9-]+$', clean_text):
                        continue
                    
                    # Avoid duplicates but keep best confidence
                    if clean_text not in seen_texts:
                        seen_texts.add(clean_text)
                        filtered_results.append({
                            'text': clean_text,
                            'confidence': confidence,
                            'bbox': bbox,
                            'source': source
                        })
                    else:
                        # Update if this has higher confidence
                        for existing in filtered_results:
                            if existing['text'] == clean_text and confidence > existing['confidence']:
                                existing['confidence'] = confidence
                                existing['source'] = source
                                break
            
            # Sort by confidence
            filtered_results.sort(key=lambda x: x['confidence'], reverse=True)
            
            self.logger.info(f"EasyOCR extracted {len(filtered_results)} text elements from {image_path} (including rotations)")
            return filtered_results
            
        except Exception as e:
            self.logger.error(f"EasyOCR text extraction failed for {image_path}: {e}")
            return []
    
    def _analyze_image_sync(self, image_path: str) -> Dict[str, Any]:
        """Synchronous image analysis (to be run in thread pool)"""
        if not self.reader:
            return {
                'success': False,
                'error': 'EasyOCR not configured or unavailable',
                'file_type': 'PRODUCT_IMAGE',
                'extraction_method': 'easyocr'
            }
        
        try:
            # Extract text with confidence scores (includes rotation handling)
            ocr_results = self.extract_text_with_confidence(image_path)
            
            if not ocr_results:
                return {
                    'success': False,
                    'error': 'No text extracted from image',
                    'file_type': 'PRODUCT_IMAGE',
                    'extraction_method': 'easyocr'
                }
            
            # Combine all extracted text
            all_text = ' '.join([result['text'] for result in ocr_results])
            
            # Extract structured data using pattern matching
            extracted_data = extract_all_data(all_text)
            
            # Add OCR-specific metadata
            high_confidence_text = [r['text'] for r in ocr_results if r['confidence'] > 0.7]
            avg_confidence = sum(r['confidence'] for r in ocr_results) / len(ocr_results)
            
            # Group results by source (original, rotated, etc.)
            sources = {}
            for result in ocr_results:
                source = result.get('source', 'unknown')
                if source not in sources:
                    sources[source] = []
                sources[source].append(result['text'])
            
            result = {
                'success': True,
                'file_type': 'PRODUCT_IMAGE',
                'extraction_method': 'easyocr_with_rotation',
                'raw_text': all_text,
                'ocr_confidence': avg_confidence,
                'high_confidence_elements': high_confidence_text,
                'total_text_elements': len(ocr_results),
                'extraction_sources': sources,
                'image_info': self._get_image_info(image_path),
                **extracted_data
            }
            
            self.logger.info(f"EasyOCR analysis completed for {image_path}")
            self.logger.debug(f"Extracted {len(ocr_results)} elements from {len(sources)} sources")
            
            return result
            
        except Exception as e:
            self.logger.error(f"EasyOCR analysis failed for {image_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'file_type': 'PRODUCT_IMAGE',
                'extraction_method': 'easyocr'
            }
    
    async def analyze_manufacturing_image(self, image_path: str) -> Dict[str, Any]:
        """
        Analyze manufacturing image using EasyOCR to extract QC data (ASYNC)
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary containing extracted manufacturing data
        """
        if not self.reader:
            self.logger.error("EasyOCR reader not available - analysis cannot proceed")
            return {
                'success': False,
                'error': 'EasyOCR not configured or unavailable',
                'file_type': 'PRODUCT_IMAGE',
                'extraction_method': 'easyocr'
            }
        
        try:
            # Run the synchronous OCR processing in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor, 
                self._analyze_image_sync, 
                image_path
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Async EasyOCR analysis failed for {image_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'file_type': 'PRODUCT_IMAGE',
                'extraction_method': 'easyocr'
            }
    
    def _get_image_info(self, image_path: str) -> Dict[str, Any]:
        """Get basic image information"""
        try:
            with Image.open(image_path) as img:
                return {
                    'width': img.width,
                    'height': img.height,
                    'mode': img.mode,
                    'format': img.format,
                    'file_size': Path(image_path).stat().st_size
                }
        except Exception as e:
            self.logger.error(f"Failed to get image info for {image_path}: {e}")
            return {}
    
    async def extract_product_image_data(self, file_path: str) -> Dict[str, Any]:
        """Main entry point for image data extraction (compatible with existing interface)"""
        return await self.analyze_manufacturing_image(file_path)
    
    def validate_image(self, file_path: str) -> Dict[str, Any]:
        """Validate that the image is readable and suitable for analysis"""
        if not Path(file_path).exists():
            return {
                'valid': False,
                'error': 'File does not exist'
            }
        
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                
                if width < 100 or height < 100:
                    return {
                        'valid': False,
                        'error': 'Image too small for reliable OCR'
                    }
                
                return {
                    'valid': True,
                    'width': width,
                    'height': height,
                    'mode': img.mode,
                    'format': img.format,
                    'analysis_method': 'easyocr' if self.reader else 'unavailable'
                }
                
        except Exception as e:
            return {
                'valid': False,
                'error': f'Image validation failed: {str(e)}'
            }
