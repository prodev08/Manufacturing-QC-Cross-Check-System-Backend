from sqlalchemy import Column, String, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.database import Base


class SessionStatus(str, enum.Enum):
    UPLOADING = 'UPLOADING'
    PROCESSING = 'PROCESSING' 
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'


class OverallResult(str, enum.Enum):
    PASS = 'PASS'
    WARNING = 'WARNING'
    FAIL = 'FAIL'


class Session(Base):
    __tablename__ = 'sessions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    status = Column(Enum(SessionStatus), default=SessionStatus.UPLOADING, nullable=False)
    overall_result = Column(Enum(OverallResult), nullable=True)
    
    # Relationships
    files = relationship('UploadedFile', back_populates='session', cascade='all, delete-orphan')
    validation_results = relationship('ValidationResult', back_populates='session', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Session {self.id} - {self.status}>'
