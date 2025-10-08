from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum

class SeverityLevel(str, Enum):
    """严重程度等级"""
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    CRITICAL = "critical"

class Season(str, Enum):
    """季节枚举"""
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"

class VisualSymptomChecklist(BaseModel):
    """视觉症状检查清单"""
    leaf_color_changes: List[str] = Field(default_factory=list, description="叶片颜色变化")
    leaf_spots_patterns: List[str] = Field(default_factory=list, description="叶片斑点模式")
    leaf_texture_changes: List[str] = Field(default_factory=list, description="叶片质地变化")
    fruit_conditions: List[str] = Field(default_factory=list, description="果实状况")
    stem_conditions: List[str] = Field(default_factory=list, description="茎干状况")
    root_conditions: List[str] = Field(default_factory=list, description="根系状况")
    overall_health_indicators: List[str] = Field(default_factory=list, description="整体健康指标")

class EnvironmentalTriggersChecklist(BaseModel):
    """环境触发因素检查清单"""
    temperature_range: Dict[str, float] = Field(default_factory=dict, description="温度范围")
    humidity_range: Dict[str, float] = Field(default_factory=dict, description="湿度范围")
    rainfall_conditions: List[str] = Field(default_factory=list, description="降雨条件")
    soil_ph_range: Dict[str, float] = Field(default_factory=dict, description="土壤pH范围")
    soil_moisture_conditions: List[str] = Field(default_factory=list, description="土壤湿度条件")
    wind_conditions: List[str] = Field(default_factory=list, description="风力条件")
    sunlight_requirements: List[str] = Field(default_factory=list, description="阳光要求")
    seasonal_preferences: List[Season] = Field(default_factory=list, description="季节性偏好")

class SymptomProgressionPattern(BaseModel):
    """症状发展模式"""
    initial_symptoms: List[str] = Field(default_factory=list, description="初期症状")
    progression_stages: List[Dict[str, Any]] = Field(default_factory=list, description="发展阶段")
    typical_duration: Optional[str] = Field(None, description="典型持续时间")
    severity_indicators: List[str] = Field(default_factory=list, description="严重程度指标")

class TreatmentProfile(BaseModel):
    """治疗方案档案"""
    chemical_treatments: List[Dict[str, Any]] = Field(default_factory=list, description="化学治疗")
    biological_treatments: List[Dict[str, Any]] = Field(default_factory=list, description="生物治疗")
    cultural_practices: List[str] = Field(default_factory=list, description="栽培措施")
    prevention_measures: List[str] = Field(default_factory=list, description="预防措施")
    treatment_effectiveness: Dict[str, float] = Field(default_factory=dict, description="治疗效果")
    side_effects: List[str] = Field(default_factory=list, description="副作用")

class DiseaseProfile(BaseModel):
    """病害特征档案 - 核心数据结构"""
    # 基本信息
    disease_id: str = Field(..., description="病害唯一标识")
    disease_name: str = Field(..., description="病害名称")
    scientific_name: Optional[str] = Field(None, description="学名")
    common_names: List[str] = Field(default_factory=list, description="常用名称")
    category: str = Field(..., description="病害类别")
    severity_level: SeverityLevel = Field(..., description="严重程度等级")
    
    # 特征描述
    description: str = Field(..., description="病害描述")
    visual_symptoms_checklist: VisualSymptomChecklist = Field(default_factory=VisualSymptomChecklist, description="视觉症状检查清单")
    environmental_triggers_checklist: EnvironmentalTriggersChecklist = Field(default_factory=EnvironmentalTriggersChecklist, description="环境触发因素检查清单")
    symptom_progression: SymptomProgressionPattern = Field(default_factory=SymptomProgressionPattern, description="症状发展模式")
    
    # 诊断特征
    key_diagnostic_features: List[str] = Field(default_factory=list, description="关键诊断特征")
    differential_diagnosis: List[str] = Field(default_factory=list, description="鉴别诊断")
    diagnostic_confidence_factors: List[str] = Field(default_factory=list, description="诊断置信度因子")
    
    # 治疗方案
    treatment_profile: TreatmentProfile = Field(default_factory=TreatmentProfile, description="治疗方案档案")
    
    # 元数据
    created_at: Optional[str] = Field(None, description="创建时间")
    updated_at: Optional[str] = Field(None, description="更新时间")
    source: Optional[str] = Field(None, description="数据来源")
    reliability_score: float = Field(1.0, ge=0.0, le=1.0, description="可靠性评分")
    
    def calculate_match_score(self, evidence_matrix: 'EvidenceMatrix') -> float:
        """计算与证据矩阵的匹配度"""
        # 这里将在后续实现具体的匹配算法
        # 暂时返回一个基础评分
        return 0.0

class DiseaseProfileCreate(BaseModel):
    """创建病害档案的请求模型"""
    disease_name: str
    scientific_name: Optional[str] = None
    common_names: List[str] = []
    category: str
    severity_level: SeverityLevel
    description: str
    source: Optional[str] = None

class DiseaseProfileUpdate(BaseModel):
    """更新病害档案的请求模型"""
    disease_name: Optional[str] = None
    scientific_name: Optional[str] = None
    common_names: Optional[List[str]] = None
    category: Optional[str] = None
    severity_level: Optional[SeverityLevel] = None
    description: Optional[str] = None
    source: Optional[str] = None

class DiseaseProfileInDBBase(DiseaseProfile):
    """数据库中的病害档案基础模型"""
    id: int
    created_at: str
    updated_at: str

class DiseaseProfileInDB(DiseaseProfileInDBBase):
    """数据库中的病害档案完整模型"""
    pass
