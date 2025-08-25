from sqlalchemy import Column, String, DateTime, Enum, Text, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.database import Base


class ValidationStatus(str, enum.Enum):
    PASS = 'PASS'
    WARNING = 'WARNING'
    FAIL = 'FAIL'


class CheckType(str, enum.Enum):
    JOB_NUMBER = 'JOB_NUMBER'
    PART_NUMBER = 'PART_NUMBER'
    REVISION = 'REVISION'
    BOARD_SERIAL = 'BOARD_SERIAL'
    UNIT_SERIAL = 'UNIT_SERIAL'
    FLIGHT_STATUS = 'FLIGHT_STATUS'
    FILE_COMPLETENESS = 'FILE_COMPLETENESS'


class ValidationResult(Base):
    __tablename__ = 'validation_results'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id'), nullable=False)
    
    # Validation details
    check_type = Column(Enum(CheckType), nullable=False)
    status = Column(Enum(ValidationStatus), nullable=False)
    description = Column(Text, nullable=False)
    
    # Source information
    source_files = Column(ARRAY(String), nullable=True)  # Array of file IDs or filenames
    expected_value = Column(String(500), nullable=True)
    actual_value = Column(String(500), nullable=True)
    
    # Additional context
    details = Column(Text, nullable=True)  # Additional details or error messages
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    session = relationship('Session', back_populates='validation_results')
    
    def __repr__(self):
        return f'<ValidationResult {self.check_type} - {self.status}>'
