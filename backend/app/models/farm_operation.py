import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Date, TEXT
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base

class FarmOperation(Base):
    __tablename__ = "farm_operations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    orchard_id = Column(UUID(as_uuid=True), ForeignKey("orchards.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    diagnosis_id = Column(UUID(as_uuid=True), ForeignKey("diagnoses.id"), nullable=True)

    type = Column(String)
    description = Column(TEXT)
    materials_used = Column(ARRAY(String))
    operation_date = Column(Date)
    image_urls = Column(ARRAY(String), nullable=True)
    
    effectiveness_rating = Column(String, nullable=True)
    feedback_details = Column(TEXT, nullable=True)
    follow_up_image_urls = Column(ARRAY(String), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    diagnosis = relationship("Diagnosis", back_populates="farm_operations")
