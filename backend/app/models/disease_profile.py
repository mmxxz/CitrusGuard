from sqlalchemy import Column, Integer, String, Text, Float, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base
from app.schemas.disease_profile import SeverityLevel, Season

class DiseaseProfile(Base):
    """病害特征档案数据库模型"""
    __tablename__ = "disease_profiles"

    id = Column(Integer, primary_key=True, index=True)
    disease_id = Column(String(100), unique=True, index=True, nullable=False)
    disease_name = Column(String(200), nullable=False, index=True)
    scientific_name = Column(String(200), nullable=True)
    common_names = Column(JSONB, nullable=True)  # 存储常用名称列表
    category = Column(String(100), nullable=False, index=True)
    severity_level = Column(SQLEnum(SeverityLevel), nullable=False)
    description = Column(Text, nullable=False)
    
    # 视觉症状检查清单
    visual_symptoms_checklist = Column(JSONB, nullable=True)
    
    # 环境触发因素检查清单
    environmental_triggers_checklist = Column(JSONB, nullable=True)
    
    # 症状发展模式
    symptom_progression = Column(JSONB, nullable=True)
    
    # 诊断特征
    key_diagnostic_features = Column(JSONB, nullable=True)
    differential_diagnosis = Column(JSONB, nullable=True)
    diagnostic_confidence_factors = Column(JSONB, nullable=True)
    
    # 治疗方案
    treatment_profile = Column(JSONB, nullable=True)
    
    # 元数据
    source = Column(String(200), nullable=True)
    reliability_score = Column(Float, default=1.0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<DiseaseProfile(id={self.id}, disease_name='{self.disease_name}')>"
