from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.disease_profile import DiseaseProfile as DiseaseProfileModel
from app.schemas.disease_profile import DiseaseProfileCreate, DiseaseProfileUpdate, DiseaseProfile as DiseaseProfileSchema
from app.schemas.evidence import EvidenceMatrix
import json

class DiseaseProfileCRUD:
    """病害档案CRUD操作类"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, disease_profile: DiseaseProfileCreate) -> DiseaseProfileModel:
        """创建新的病害档案"""
        # 生成唯一的disease_id
        disease_id = f"disease_{disease_profile.disease_name.lower().replace(' ', '_')}"
        
        db_disease_profile = DiseaseProfileModel(
            disease_id=disease_id,
            disease_name=disease_profile.disease_name,
            scientific_name=disease_profile.scientific_name,
            common_names=disease_profile.common_names,
            category=disease_profile.category,
            severity_level=disease_profile.severity_level,
            description=disease_profile.description,
            source=disease_profile.source
        )
        
        self.db.add(db_disease_profile)
        self.db.commit()
        self.db.refresh(db_disease_profile)
        return db_disease_profile
    
    def get_by_id(self, disease_id: int) -> Optional[DiseaseProfileModel]:
        """根据ID获取病害档案"""
        return self.db.query(DiseaseProfileModel).filter(DiseaseProfileModel.id == disease_id).first()
    
    def get_by_disease_id(self, disease_id: str) -> Optional[DiseaseProfileModel]:
        """根据disease_id获取病害档案"""
        return self.db.query(DiseaseProfileModel).filter(DiseaseProfileModel.disease_id == disease_id).first()
    
    def get_by_name(self, disease_name: str) -> Optional[DiseaseProfileModel]:
        """根据病害名称获取病害档案"""
        return self.db.query(DiseaseProfileModel).filter(DiseaseProfileModel.disease_name == disease_name).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[DiseaseProfileModel]:
        """获取所有病害档案"""
        return self.db.query(DiseaseProfileModel).offset(skip).limit(limit).all()
    
    def search_by_name(self, name_query: str, skip: int = 0, limit: int = 100) -> List[DiseaseProfileModel]:
        """根据名称搜索病害档案"""
        return self.db.query(DiseaseProfileModel).filter(
            or_(
                DiseaseProfileModel.disease_name.ilike(f"%{name_query}%"),
                DiseaseProfileModel.scientific_name.ilike(f"%{name_query}%")
            )
        ).offset(skip).limit(limit).all()
    
    def search_by_category(self, category: str, skip: int = 0, limit: int = 100) -> List[DiseaseProfileModel]:
        """根据类别搜索病害档案"""
        return self.db.query(DiseaseProfileModel).filter(
            DiseaseProfileModel.category == category
        ).offset(skip).limit(limit).all()
    
    def search_by_symptoms(self, symptoms: List[str], skip: int = 0, limit: int = 100) -> List[DiseaseProfileModel]:
        """根据症状搜索病害档案"""
        # 这里需要实现更复杂的JSON查询逻辑
        # 暂时使用简单的文本搜索
        query = self.db.query(DiseaseProfileModel)
        for symptom in symptoms:
            query = query.filter(
                or_(
                    DiseaseProfileModel.description.ilike(f"%{symptom}%"),
                    DiseaseProfileModel.visual_symptoms_checklist.op('?')(symptom)
                )
            )
        return query.offset(skip).limit(limit).all()
    
    def update(self, disease_id: int, disease_profile_update: DiseaseProfileUpdate) -> Optional[DiseaseProfileModel]:
        """更新病害档案"""
        db_disease_profile = self.get_by_id(disease_id)
        if not db_disease_profile:
            return None
        
        update_data = disease_profile_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_disease_profile, field, value)
        
        self.db.commit()
        self.db.refresh(db_disease_profile)
        return db_disease_profile
    
    def delete(self, disease_id: int) -> bool:
        """删除病害档案"""
        db_disease_profile = self.get_by_id(disease_id)
        if not db_disease_profile:
            return False
        
        self.db.delete(db_disease_profile)
        self.db.commit()
        return True
    
    def get_candidates_for_evidence(self, evidence_matrix: EvidenceMatrix, limit: int = 10) -> List[DiseaseProfileModel]:
        """根据证据矩阵获取候选病害档案"""
        # 这里将实现基于证据矩阵的智能匹配算法
        # 暂时返回所有档案，后续会实现具体的匹配逻辑
        return self.db.query(DiseaseProfileModel).limit(limit).all()
    
    def calculate_match_score(self, disease_profile: DiseaseProfileModel, evidence_matrix: EvidenceMatrix) -> float:
        """计算病害档案与证据矩阵的匹配度"""
        # 这里将实现具体的匹配算法
        # 暂时返回一个随机分数
        import random
        return random.uniform(0.0, 1.0)

# 创建CRUD实例的工厂函数
def get_disease_profile_crud(db: Session) -> DiseaseProfileCRUD:
    return DiseaseProfileCRUD(db)
