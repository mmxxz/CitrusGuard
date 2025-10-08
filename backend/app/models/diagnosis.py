import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, TEXT, Float
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base

class DiagnosisSession(Base):
    __tablename__ = "diagnosis_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    orchard_id = Column(UUID(as_uuid=True), ForeignKey("orchards.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, default="ongoing")
    initial_query = Column(TEXT, nullable=True)
    initial_image_urls = Column(ARRAY(String), nullable=True)

    orchard = relationship("Orchard", back_populates="diagnosis_sessions")
    messages = relationship("DiagnosisMessage", back_populates="session")
    result = relationship("Diagnosis", back_populates="session", uselist=False)

class DiagnosisMessage(Base):
    __tablename__ = "diagnosis_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("diagnosis_sessions.id"), nullable=False)

    sender = Column(String, nullable=False) # "user" or "ai"
    content_text = Column(TEXT, nullable=True)
    content_image_urls = Column(ARRAY(String), nullable=True)
    message_type = Column(String, default="text")
    agent_workflow_state = Column(JSONB, nullable=True)
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("DiagnosisSession", back_populates="messages")

class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("diagnosis_sessions.id"), unique=True, nullable=False)
    
    primary_diagnosis = Column(String)
    confidence = Column(Float)
    secondary_diagnoses = Column(JSONB)
    prevention_advice = Column(TEXT)
    treatment_advice = Column(TEXT)
    follow_up_plan = Column(TEXT)
    original_image_urls = Column(ARRAY(String))
    
    # 新增字段：病例管理
    maintenance_advice = Column(TEXT, nullable=True)
    severity_level = Column(String, nullable=True)  # 'high', 'medium', 'low'
    case_status = Column(String, nullable=True, default='active')  # 'active', 'resolved', 'monitoring'
    last_maintenance_date = Column(DateTime(timezone=True), nullable=True)
    maintenance_history = Column(JSONB, nullable=True)

    generated_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("DiagnosisSession", back_populates="result")
    farm_operations = relationship("FarmOperation", back_populates="diagnosis")
