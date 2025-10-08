#!/usr/bin/env python3
"""
根据结构化数据.json更新病害档案
将82个病虫害条目转换为结构化的DiseaseProfile数据
"""

import sys
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

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

def load_structured_data(file_path: str) -> List[Dict[str, Any]]:
    """加载结构化数据JSON文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"成功加载 {len(data)} 个病虫害条目")
        return data
    except Exception as e:
        print(f"加载JSON文件失败: {e}")
        return []

def extract_visual_symptoms(symptoms_data: List[Dict]) -> VisualSymptomChecklist:
    """从症状数据中提取视觉症状检查清单"""
    visual_symptoms = VisualSymptomChecklist()
    
    for symptom in symptoms_data:
        if "部位" in symptom:
            body_part = symptom["部位"]
            
            if "枝梢和叶片" in body_part or "叶片" in body_part or "枝梢" in body_part:
                # 提取叶片相关症状
                if "阶段" in symptom:
                    for stage in symptom["阶段"]:
                        if "描述" in stage:
                            description = stage["描述"]
                            # 提取颜色变化
                            if "黄" in description or "绿" in description or "褐" in description:
                                visual_symptoms.leaf_color_changes.append(description)
                            # 提取斑点模式
                            if "斑" in description or "点" in description:
                                visual_symptoms.leaf_spots_patterns.append(description)
                            # 提取质地变化
                            if "小" in description or "厚" in description or "薄" in description:
                                visual_symptoms.leaf_texture_changes.append(description)
                
                if "类型" in symptom:
                    for type_info in symptom["类型"]:
                        if "特征" in type_info:
                            feature = type_info["特征"]
                            if "黄" in feature or "绿" in feature or "褐" in feature:
                                visual_symptoms.leaf_color_changes.append(feature)
                            if "斑" in feature or "点" in feature:
                                visual_symptoms.leaf_spots_patterns.append(feature)
            
            elif "果实" in body_part:
                # 提取果实相关症状
                if "类型" in symptom:
                    for type_info in symptom["类型"]:
                        if "特征" in type_info:
                            feature = type_info["特征"]
                            visual_symptoms.fruit_conditions.append(feature)
                        if "类型名称" in type_info:
                            type_name = type_info["类型名称"]
                            visual_symptoms.fruit_conditions.append(type_name)
            
            elif "枝干" in body_part or "砧木" in body_part:
                # 提取枝干相关症状
                if "类型" in symptom:
                    for type_info in symptom["类型"]:
                        if "特征" in type_info:
                            feature = type_info["特征"]
                            visual_symptoms.stem_conditions.append(feature)
    
    return visual_symptoms

def extract_environmental_triggers(occurrence_data: Dict) -> EnvironmentalTriggersChecklist:
    """从发生规律数据中提取环境触发因素"""
    env_triggers = EnvironmentalTriggersChecklist()
    
    if "流行条件" in occurrence_data:
        conditions = occurrence_data["流行条件"]
        
        # 提取温度范围
        if "温度范围" in conditions and conditions["温度范围"] != "未明确":
            temp_range = conditions["温度范围"]
            # 解析温度范围，如 "22~24℃或27~32℃"
            if "~" in temp_range:
                parts = temp_range.split("~")
                if len(parts) >= 2:
                    try:
                        min_temp = float(parts[0].replace("℃", ""))
                        max_temp = float(parts[1].split("℃")[0])
                        env_triggers.temperature_range = {"min": min_temp, "max": max_temp}
                    except:
                        pass
        
        # 提取湿度范围
        if "湿度范围" in conditions and conditions["湿度范围"] != "未明确":
            humidity_range = conditions["湿度范围"]
            if "~" in humidity_range:
                parts = humidity_range.split("~")
                if len(parts) >= 2:
                    try:
                        min_humidity = float(parts[0].replace("%", ""))
                        max_humidity = float(parts[1].split("%")[0])
                        env_triggers.humidity_range = {"min": min_humidity, "max": max_humidity}
                    except:
                        pass
        
        # 提取其他条件
        if "其他条件" in conditions:
            other_conditions = conditions["其他条件"]
            if "高湿" in other_conditions or "多雨" in other_conditions:
                env_triggers.rainfall_conditions.append("高湿度")
            if "干旱" in other_conditions:
                env_triggers.rainfall_conditions.append("干旱")
    
    return env_triggers

def extract_symptom_progression(symptoms_data: List[Dict]) -> SymptomProgressionPattern:
    """从症状数据中提取症状发展模式"""
    progression = SymptomProgressionPattern()
    
    for symptom in symptoms_data:
        if "阶段" in symptom:
            for stage in symptom["阶段"]:
                if "阶段名称" in stage and "描述" in stage:
                    stage_name = stage["阶段名称"]
                    description = stage["描述"]
                    
                    if stage_name == "初期":
                        progression.initial_symptoms.append(description)
                    else:
                        progression.progression_stages.append({
                            "stage": stage_name,
                            "symptoms": [description]
                        })
    
    return progression

def extract_treatment_profile(control_methods: List[Dict]) -> TreatmentProfile:
    """从防治方法数据中提取治疗方案"""
    treatment = TreatmentProfile()
    
    for method in control_methods:
        if "方法分类" in method and "具体措施" in method:
            method_type = method["方法分类"]
            measures = method["具体措施"]
            
            if method_type == "农业措施":
                treatment.cultural_practices.extend(measures)
            elif method_type == "化学防治":
                treatment.chemical_treatments.append({
                    "name": "化学防治",
                    "measures": measures,
                    "effectiveness": 0.8
                })
            elif method_type == "生物防治":
                treatment.biological_treatments.append({
                    "name": "生物防治",
                    "measures": measures,
                    "effectiveness": 0.6
                })
            elif method_type == "检疫措施":
                treatment.prevention_measures.extend(measures)
    
    return treatment

def determine_severity_level(name: str, category: str) -> SeverityLevel:
    """根据名称和分类确定严重程度等级"""
    name_lower = name.lower()
    category_lower = category.lower()
    
    # 严重病害
    if any(keyword in name_lower for keyword in ["黄龙病", "衰退病", "裂皮病", "溃疡病"]):
        return SeverityLevel.CRITICAL
    
    # 严重虫害
    if any(keyword in name_lower for keyword in ["红蜘蛛", "锈壁虱", "潜叶蛾"]):
        return SeverityLevel.SEVERE
    
    # 中等严重
    if any(keyword in name_lower for keyword in ["炭疽病", "黑斑病", "疮痂病"]):
        return SeverityLevel.MODERATE
    
    # 轻微
    return SeverityLevel.MILD

def convert_to_disease_profile(item: Dict[str, Any]) -> DiseaseProfileCreate:
    """将JSON条目转换为DiseaseProfileCreate"""
    
    # 基本信息
    name = item.get("名称", "")
    category = item.get("分类", "其他")
    aliases = item.get("别名", [])
    
    # 确定严重程度
    severity = determine_severity_level(name, category)
    
    # 构建描述
    description_parts = []
    
    # 添加症状描述
    if "症状" in item:
        symptom_descriptions = []
        for symptom in item["症状"]:
            if "部位" in symptom and "阶段" in symptom:
                for stage in symptom["阶段"]:
                    if "描述" in stage:
                        symptom_descriptions.append(f"{symptom['部位']}: {stage['描述']}")
        if symptom_descriptions:
            description_parts.append("症状: " + "; ".join(symptom_descriptions[:3]))
    
    # 添加病原信息
    if "病原" in item and "类型" in item["病原"]:
        pathogen_type = item["病原"]["类型"]
        description_parts.append(f"病原: {pathogen_type}")
    
    description = ". ".join(description_parts) if description_parts else f"{name}的详细信息"
    
    return DiseaseProfileCreate(
        disease_name=name,
        scientific_name=None,  # JSON中没有学名信息
        common_names=aliases,
        category=category,
        severity_level=severity,
        description=description,
        source="结构化数据.json"
    )

def enrich_disease_profile_with_detailed_data(db_profile: DiseaseProfileModel, item: Dict[str, Any]) -> DiseaseProfileModel:
    """用详细数据丰富病害档案"""
    
    # 提取视觉症状
    if "症状" in item:
        visual_symptoms = extract_visual_symptoms(item["症状"])
        db_profile.visual_symptoms_checklist = visual_symptoms.model_dump()
    
    # 提取环境触发因素
    if "发生规律" in item:
        env_triggers = extract_environmental_triggers(item["发生规律"])
        db_profile.environmental_triggers_checklist = env_triggers.model_dump()
    
    # 提取症状发展模式
    if "症状" in item:
        progression = extract_symptom_progression(item["症状"])
        db_profile.symptom_progression = progression.model_dump()
    
    # 提取治疗方案
    if "防治方法" in item:
        treatment = extract_treatment_profile(item["防治方法"])
        db_profile.treatment_profile = treatment.model_dump()
    
    # 提取关键诊断特征
    key_features = []
    if "症状" in item:
        for symptom in item["症状"]:
            if "类型" in symptom:
                for type_info in symptom["类型"]:
                    if "特征" in type_info:
                        key_features.append(type_info["特征"])
    db_profile.key_diagnostic_features = key_features[:10]  # 限制数量
    
    # 提取鉴别诊断信息
    differential_diagnosis = []
    if "别名" in item:
        differential_diagnosis.extend(item["别名"])
    db_profile.differential_diagnosis = differential_diagnosis
    
    # 设置诊断置信度因子
    confidence_factors = []
    if "病原" in item and "类型" in item["病原"]:
        confidence_factors.append(f"病原类型: {item['病原']['类型']}")
    if "发生规律" in item and "寄主范围" in item["发生规律"]:
        confidence_factors.append("寄主范围信息")
    db_profile.diagnostic_confidence_factors = confidence_factors
    
    return db_profile

def update_disease_profiles():
    """更新病害档案数据库"""
    
    # 加载结构化数据
    json_file_path = "/Users/letaotao/Desktop/CitrusGuard/结构化数据.json"
    structured_data = load_structured_data(json_file_path)
    
    if not structured_data:
        print("没有加载到数据，退出")
        return
    
    db = SessionLocal()
    
    try:
        # 清空现有数据
        print("清空现有病害档案数据...")
        db.query(DiseaseProfileModel).delete()
        db.commit()
        
        # 转换和插入新数据
        success_count = 0
        error_count = 0
        
        for i, item in enumerate(structured_data, 1):
            try:
                print(f"处理第 {i}/{len(structured_data)} 个条目: {item.get('名称', 'Unknown')}")
                
                # 转换为DiseaseProfileCreate
                profile_create = convert_to_disease_profile(item)
                
                # 创建基础档案
                disease_id = f"disease_{profile_create.disease_name.lower().replace(' ', '_').replace('(', '').replace(')', '')}"
                
                db_profile = DiseaseProfileModel(
                    disease_id=disease_id,
                    disease_name=profile_create.disease_name,
                    scientific_name=profile_create.scientific_name,
                    common_names=profile_create.common_names,
                    category=profile_create.category,
                    severity_level=profile_create.severity_level,
                    description=profile_create.description,
                    source=profile_create.source
                )
                
                # 丰富详细信息
                db_profile = enrich_disease_profile_with_detailed_data(db_profile, item)
                
                db.add(db_profile)
                success_count += 1
                
            except Exception as e:
                print(f"处理第 {i} 个条目时出错: {e}")
                error_count += 1
                continue
        
        # 提交所有更改
        db.commit()
        print(f"\n更新完成!")
        print(f"成功处理: {success_count} 个条目")
        print(f"处理失败: {error_count} 个条目")
        
        # 验证结果
        total_count = db.query(DiseaseProfileModel).count()
        print(f"数据库中现有病害档案数量: {total_count}")
        
    except Exception as e:
        print(f"更新数据库时发生错误: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    update_disease_profiles()
