import base64
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from PIL import Image
from openai import OpenAI
import re
import json

from app.config import settings
from app.utils.patterns import extract_all_data

logger = logging.getLogger(__name__)


class OpenAIVisionService:
    """Service for image analysis using OpenAI GPT-4V"""
    
    def __init__(self):
        self.logger = logger
        
        if not settings.openai_api_key:
            self.logger.warning("OpenAI API key not configured")
            self.client = None
        else:
            try:
                self.client = OpenAI(api_key=settings.openai_api_key)
                self.logger.info("OpenAI Vision service initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize OpenAI client: {e}")
                self.client = None
    
    def encode_image(self, image_path: str) -> str:
        """Encode image to base64 string"""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            self.logger.error(f"Failed to encode image {image_path}: {e}")
            raise
    
    async def analyze_manufacturing_image(self, image_path: str) -> Dict[str, Any]:
        """
        Analyze manufacturing image using GPT-4o to extract QC data
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary containing extracted manufacturing data
        """
        if not self.client:
            self.logger.error("OpenAI client not available - analysis cannot proceed")
            return {
                'success': False,
                'error': 'OpenAI client not configured or unavailable',
                'file_type': 'PRODUCT_IMAGE',
                'extraction_method': 'openai_gpt4o'
            }
        
        try:
            # Encode the image
            base64_image = self.encode_image(image_path)
            
            # Create the prompt for manufacturing QC analysis
            prompt = self._create_manufacturing_prompt()
            
            # Call OpenAI Vision API asynchronously
            response = await self.client.chat.completions.create(
                model="gpt-4o",  # Use the latest GPT-4o model
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000,
                temperature=0.1  # Low temperature for consistent extraction
            )
            
            # Parse the response
            analysis_text = response.choices[0].message.content
            self.logger.info(f"OpenAI analysis completed for {image_path}")
            self.logger.debug(f"Raw analysis: {analysis_text}")
            
            # Extract structured data from the analysis
            extracted_data = self._parse_openai_response(analysis_text)
            
            return {
                'success': True,
                'file_type': 'PRODUCT_IMAGE',
                'extraction_method': 'openai_gpt4o',
                'raw_analysis': analysis_text,
                'image_info': self._get_image_info(image_path),
                **extracted_data
            }
            
        except Exception as e:
            self.logger.error(f"OpenAI vision analysis failed for {image_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'file_type': 'PRODUCT_IMAGE',
                'extraction_method': 'openai_gpt4o'
            }
    
    def _create_manufacturing_prompt(self) -> str:
        """Create a specialized prompt for manufacturing QC image analysis"""
        return """
You are analyzing a manufacturing/electronics hardware image for Quality Control purposes. 
Please extract the following specific information if visible:

1. **Board Serials**: Look for patterns like "VGN-XXXXX-XXXX" or similar serial numbers on circuit boards
2. **Part Numbers**: Look for patterns like "PCA-XXXX-YY" or "DRW-XXXX-YY" on components or labels  
3. **Unit Serials**: Look for patterns like "INF-XXXX" or similar unit identification numbers
4. **Job Numbers**: Look for 5-digit numbers that might represent job/work order numbers
5. **Flight Status**: Look for text like "FLIGHT", "EDU - NOT FOR FLIGHT", or similar flight certification markings
6. **Revisions**: Look for revision markings like "Rev A", "Rev F2", "Rev E", etc.

Please provide your analysis in this exact JSON format:
{
  "board_serials": ["list of found board serials"],
  "part_numbers": ["list of found part numbers"],  
  "unit_serials": ["list of found unit serials"],
  "job_numbers": ["list of found job numbers"],
  "flight_status": ["list of found flight status markings"],
  "revisions": ["list of found revision markings"],
  "confidence": "high/medium/low",
  "notes": "any additional observations about the image quality or extraction confidence"
}

Important: Only include data you can clearly read. If text is unclear or uncertain, note it in the confidence and notes fields.
"""
    
    def _parse_openai_response(self, response_text: str) -> Dict[str, Any]:
        """Parse OpenAI response and extract structured data"""
        try:
            # Try to find JSON in the response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
                
                # Ensure all required fields exist with defaults
                result = {
                    'board_serials': data.get('board_serials', []),
                    'part_numbers': data.get('part_numbers', []),
                    'unit_serials': data.get('unit_serials', []),
                    'job_numbers': data.get('job_numbers', []),
                    'flight_status': data.get('flight_status', []),
                    'revisions': data.get('revisions', []),
                    'confidence': data.get('confidence', 'medium'),
                    'notes': data.get('notes', '')
                }
                
                return result
            else:
                # Fallback: try to extract using regex patterns
                self.logger.warning("No JSON found in OpenAI response, using pattern extraction")
                return extract_all_data(response_text)
                
        except Exception as e:
            self.logger.error(f"Failed to parse OpenAI response: {e}")
            # Fallback to pattern extraction on raw text
            return extract_all_data(response_text)
    
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
                        'error': 'Image too small for reliable analysis'
                    }
                
                return {
                    'valid': True,
                    'width': width,
                    'height': height,
                    'mode': img.mode,
                    'format': img.format,
                    'analysis_method': 'openai_gpt4o' if self.client else 'unavailable'
                }
                
        except Exception as e:
            return {
                'valid': False,
                'error': f'Image validation failed: {str(e)}'
            }
