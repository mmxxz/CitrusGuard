import uuid
from sqlalchemy import Column, String, Float, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    orchard_id = Column(UUID(as_uuid=True), ForeignKey("orchards.id"), nullable=False)

    type = Column(String)
    risk_item = Column(String)
    risk_level = Column(String)
    confidence = Column(Float)
    reason = Column(String)
    status = Column(String, default="active")
    
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    ignored_at = Column(DateTime(timezone=True), nullable=True)

    orchard = relationship("Orchard", back_populates="alerts")
