import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Configuration
    api_v1_str: str = '/api/v1'
    project_name: str = 'Manufacturing QC Cross-Check System'
    debug: bool = True
    
    # Database
    database_url: str = 'postgresql://user:password@localhost:5432/qc_system'
    
    # Redis
    redis_url: str = 'redis://localhost:6379/0'
    
    # File Storage
    upload_dir: str = './uploads'
    max_file_size: int = 50_000_000  # 50MB
    
    # Allowed file types
    allowed_image_types: set = {'image/jpeg', 'image/png', 'image/jpg'}
    allowed_pdf_types: set = {'application/pdf'}
    allowed_excel_types: set = {
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-excel'
    }
    
    class Config:
        env_file = '.env'
        case_sensitive = False


# Create upload directory if it doesn't exist
settings = Settings()
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
