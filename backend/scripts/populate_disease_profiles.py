#!/usr/bin/env python3
"""
数据填充脚本：将现有的非结构化知识转化为结构化的 DiseaseProfile
"""

import sys
import os
import json
from datetime import datetime
from typing import List, Dict, Any

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.disease_profile import DiseaseProfile as DiseaseProfileModel
from app.schemas.disease_profile import (
    DiseaseProfileCreate, 
    VisualSymptomChecklist, 
    EnvironmentalTriggersChecklist,
    SymptomProgressionPattern,
    TreatmentProfile,
    SeverityLevel,
    Season
)

def create_sample_disease_profiles() -> List[DiseaseProfileCreate]:
    """创建示例病害档案数据"""
    
    disease_profiles = [
        DiseaseProfileCreate(
            disease_name="柑橘黄龙病",
            scientific_name="Candidatus Liberibacter asiaticus",
            common_names=["黄龙病", "HLB", "柑橘黄化病"],
            category="细菌性病害",
            severity_level=SeverityLevel.CRITICAL,
            description="柑橘黄龙病是由韧皮部杆菌引起的毁灭性病害，主要症状包括叶片黄化、果实畸形、根系腐烂等。",
            source="农业知识库"
        ),
        DiseaseProfileCreate(
            disease_name="柑橘黑斑病",
            scientific_name="Guignardia citricarpa",
            common_names=["黑斑病", "黑星病"],
            category="真菌性病害",
            severity_level=SeverityLevel.MODERATE,
            description="柑橘黑斑病是由真菌引起的病害，主要影响果实外观，在叶片和果实上形成黑色斑点。",
            source="农业知识库"
        ),
        DiseaseProfileCreate(
            disease_name="柑橘溃疡病",
            scientific_name="Xanthomonas citri",
            common_names=["溃疡病", "细菌性溃疡"],
            category="细菌性病害",
            severity_level=SeverityLevel.SEVERE,
            description="柑橘溃疡病是由细菌引起的病害，在叶片、枝条和果实上形成水渍状病斑，后期病斑中央凹陷。",
            source="农业知识库"
        ),
        DiseaseProfileCreate(
            disease_name="柑橘炭疽病",
            scientific_name="Colletotrichum gloeosporioides",
            common_names=["炭疽病", "果腐病"],
            category="真菌性病害",
            severity_level=SeverityLevel.MODERATE,
            description="柑橘炭疽病是由真菌引起的病害，主要症状包括叶片枯死、果实腐烂、枝条溃疡等。",
            source="农业知识库"
        ),
        DiseaseProfileCreate(
            disease_name="柑橘红蜘蛛",
            scientific_name="Panonychus citri",
            common_names=["红蜘蛛", "螨虫"],
            category="虫害",
            severity_level=SeverityLevel.MILD,
            description="柑橘红蜘蛛是重要的害虫，主要危害叶片，导致叶片失绿、脱落，影响光合作用。",
            source="农业知识库"
        )
    ]
    
    return disease_profiles

def enrich_disease_profile(db_profile: DiseaseProfileModel, profile_data: Dict[str, Any]) -> DiseaseProfileModel:
    """丰富病害档案的详细信息"""
    
    # 根据病害类型设置不同的特征
    if "黄龙病" in db_profile.disease_name:
        # 柑橘黄龙病的详细特征
        db_profile.visual_symptoms_checklist = {
            "leaf_color_changes": ["叶片黄化", "叶脉黄化", "叶片不对称黄化"],
            "leaf_spots_patterns": ["叶脉间黄化", "叶片边缘黄化"],
            "leaf_texture_changes": ["叶片变厚", "叶片变脆"],
            "fruit_conditions": ["果实畸形", "果实变小", "果实酸度增加"],
            "stem_conditions": ["枝条枯死", "树皮开裂"],
            "root_conditions": ["根系腐烂", "根系发育不良"],
            "overall_health_indicators": ["树势衰弱", "产量下降"]
        }
        
        db_profile.environmental_triggers_checklist = {
            "temperature_range": {"min": 20, "max": 35},
            "humidity_range": {"min": 60, "max": 90},
            "rainfall_conditions": ["高湿度", "多雨季节"],
            "soil_ph_range": {"min": 5.5, "max": 7.0},
            "soil_moisture_conditions": ["排水不良", "积水"],
            "wind_conditions": ["微风", "无风"],
            "sunlight_requirements": ["充足光照", "避免强光"],
            "seasonal_preferences": [Season.SPRING, Season.SUMMER]
        }
        
        db_profile.symptom_progression = {
            "initial_symptoms": ["叶片轻微黄化", "叶脉间黄化"],
            "progression_stages": [
                {"stage": "初期", "symptoms": ["叶片黄化", "叶脉黄化"]},
                {"stage": "中期", "symptoms": ["果实畸形", "枝条枯死"]},
                {"stage": "后期", "symptoms": ["根系腐烂", "整株死亡"]}
            ],
            "typical_duration": "2-3年",
            "severity_indicators": ["叶片黄化程度", "果实畸形率", "根系状况"]
        }
        
        db_profile.key_diagnostic_features = [
            "叶片不对称黄化",
            "叶脉黄化",
            "果实畸形",
            "根系腐烂"
        ]
        
        db_profile.differential_diagnosis = [
            "缺铁黄化",
            "缺氮黄化",
            "其他病毒病"
        ]
        
        db_profile.diagnostic_confidence_factors = [
            "症状组合",
            "发病季节",
            "传播媒介",
            "PCR检测结果"
        ]
        
        db_profile.treatment_profile = {
            "chemical_treatments": [
                {"name": "抗生素治疗", "effectiveness": 0.3, "side_effects": ["抗药性"]},
                {"name": "铜制剂", "effectiveness": 0.2, "side_effects": ["药害"]}
            ],
            "biological_treatments": [
                {"name": "生物防治", "effectiveness": 0.4, "side_effects": []}
            ],
            "cultural_practices": [
                "及时清除病株",
                "加强检疫",
                "培育抗病品种"
            ],
            "prevention_measures": [
                "使用无毒苗木",
                "防治传播媒介",
                "加强田间管理"
            ],
            "treatment_effectiveness": {
                "化学治疗": 0.3,
                "生物防治": 0.4,
                "综合防治": 0.6
            },
            "side_effects": ["抗药性", "环境污染", "成本高"]
        }
    
    elif "黑斑病" in db_profile.disease_name:
        # 柑橘黑斑病的详细特征
        db_profile.visual_symptoms_checklist = {
            "leaf_color_changes": ["叶片出现黑斑", "叶片黄化"],
            "leaf_spots_patterns": ["圆形黑斑", "不规则黑斑", "同心圆状"],
            "leaf_texture_changes": ["病斑凹陷", "病斑隆起"],
            "fruit_conditions": ["果实黑斑", "果实畸形", "果实脱落"],
            "stem_conditions": ["枝条病斑"],
            "root_conditions": [],
            "overall_health_indicators": ["叶片脱落", "果实品质下降"]
        }
        
        db_profile.environmental_triggers_checklist = {
            "temperature_range": {"min": 15, "max": 30},
            "humidity_range": {"min": 70, "max": 95},
            "rainfall_conditions": ["多雨", "高湿度"],
            "soil_ph_range": {"min": 6.0, "max": 7.5},
            "soil_moisture_conditions": ["排水良好"],
            "wind_conditions": ["微风"],
            "sunlight_requirements": ["充足光照"],
            "seasonal_preferences": [Season.SUMMER, Season.AUTUMN]
        }
        
        db_profile.key_diagnostic_features = [
            "圆形黑斑",
            "同心圆状病斑",
            "果实黑斑"
        ]
        
        db_profile.treatment_profile = {
            "chemical_treatments": [
                {"name": "苯醚甲环唑", "effectiveness": 0.8, "side_effects": ["抗药性"]},
                {"name": "代森锰锌", "effectiveness": 0.7, "side_effects": ["药害"]}
            ],
            "cultural_practices": [
                "清除病残体",
                "合理修剪",
                "改善通风透光"
            ],
            "prevention_measures": [
                "选择抗病品种",
                "加强田间管理",
                "适时喷药"
            ]
        }
    
    # 其他病害的类似处理...
    
    return db_profile

def populate_database():
    """填充数据库"""
    db = SessionLocal()
    
    try:
        # 检查是否已有数据
        existing_count = db.query(DiseaseProfileModel).count()
        if existing_count > 0:
            print(f"数据库中已有 {existing_count} 条病害档案记录，跳过填充。")
            return
        
        # 创建基础病害档案
        disease_profiles = create_sample_disease_profiles()
        
        for profile_data in disease_profiles:
            # 创建基础档案
            db_profile = DiseaseProfileModel(
                disease_id=f"disease_{profile_data.disease_name.lower().replace(' ', '_')}",
                disease_name=profile_data.disease_name,
                scientific_name=profile_data.scientific_name,
                common_names=profile_data.common_names,
                category=profile_data.category,
                severity_level=profile_data.severity_level,
                description=profile_data.description,
                source=profile_data.source
            )
            
            # 丰富详细信息
            db_profile = enrich_disease_profile(db_profile, profile_data.__dict__)
            
            db.add(db_profile)
        
        db.commit()
        print(f"成功填充 {len(disease_profiles)} 条病害档案记录。")
        
    except Exception as e:
        print(f"填充数据库时发生错误: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    populate_database()
