from sqlalchemy import Column, String, DateTime, Enum, Text, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.database import Base


class FileType(str, enum.Enum):
    TRAVELER_PDF = 'TRAVELER_PDF'
    PRODUCT_IMAGE = 'PRODUCT_IMAGE'
    BOM_EXCEL = 'BOM_EXCEL'


class ProcessingStatus(str, enum.Enum):
    PENDING = 'PENDING'
    PROCESSING = 'PROCESSING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'


class UploadedFile(Base):
    __tablename__ = 'uploaded_files'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id'), nullable=False)
    
    # File metadata
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_type = Column(Enum(FileType), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_path = Column(String(500), nullable=False)  # Path to stored file
    
    # Processing status
    processing_status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING, nullable=False)
    processing_error = Column(Text, nullable=True)
    
    # Extracted data (stored as JSON)
    extracted_data = Column(JSONB, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    session = relationship('Session', back_populates='files')
    
    def __repr__(self):
        return f'<UploadedFile {self.filename} - {self.file_type}>'
