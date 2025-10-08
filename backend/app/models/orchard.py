import uuid
from sqlalchemy import Column, String, Boolean, Float, Integer, Date, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base

class Orchard(Base):
    __tablename__ = "orchards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    name = Column(String, nullable=False)
    location_latitude = Column(Float)
    location_longitude = Column(Float)
    address_detail = Column(String)
    main_variety = Column(String)
    avg_tree_age = Column(Integer)
    soil_type = Column(String)
    last_harvest_date = Column(Date)
    
    current_phenology = Column(String)
    health_score = Column(Float)
    has_new_alerts = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship("User", back_populates="orchards")
    alerts = relationship("Alert", back_populates="orchard")
    diagnosis_sessions = relationship("DiagnosisSession", back_populates="orchard")
