from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum

class EvidenceType(str, Enum):
    """证据类型枚举"""
    VISUAL = "visual"
    SYMPTOM = "symptom"
    ENVIRONMENTAL = "environmental"
    HISTORICAL = "historical"

class VisualEvidence(BaseModel):
    """视觉证据结构"""
    leaf_color: Optional[str] = Field(None, description="叶片颜色")
    leaf_spots: Optional[List[str]] = Field(default_factory=list, description="叶片斑点类型")
    leaf_texture: Optional[str] = Field(None, description="叶片质地")
    fruit_condition: Optional[str] = Field(None, description="果实状况")
    stem_condition: Optional[str] = Field(None, description="茎干状况")
    root_condition: Optional[str] = Field(None, description="根系状况")
    overall_health: Optional[str] = Field(None, description="整体健康状况")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="视觉证据置信度")

class SymptomEvidence(BaseModel):
    """症状证据结构"""
    primary_symptoms: List[str] = Field(default_factory=list, description="主要症状")
    secondary_symptoms: List[str] = Field(default_factory=list, description="次要症状")
    symptom_severity: Optional[str] = Field(None, description="症状严重程度")
    symptom_duration: Optional[str] = Field(None, description="症状持续时间")
    affected_areas: List[str] = Field(default_factory=list, description="受影响区域")
    progression_pattern: Optional[str] = Field(None, description="症状发展模式")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="症状证据置信度")

class EnvironmentalEvidence(BaseModel):
    """环境证据结构"""
    temperature: Optional[float] = Field(None, description="温度")
    humidity: Optional[float] = Field(None, description="湿度")
    rainfall: Optional[float] = Field(None, description="降雨量")
    soil_ph: Optional[float] = Field(None, description="土壤pH值")
    soil_moisture: Optional[float] = Field(None, description="土壤湿度")
    wind_speed: Optional[float] = Field(None, description="风速")
    sunlight_exposure: Optional[str] = Field(None, description="阳光照射情况")
    recent_weather_events: List[str] = Field(default_factory=list, description="近期天气事件")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="环境证据置信度")

class HistoricalEvidence(BaseModel):
    """历史证据结构"""
    similar_cases: List[Dict[str, Any]] = Field(default_factory=list, description="相似历史案例")
    previous_treatments: List[str] = Field(default_factory=list, description="历史治疗方案")
    seasonal_patterns: List[str] = Field(default_factory=list, description="季节性模式")
    outbreak_history: List[Dict[str, Any]] = Field(default_factory=list, description="疫情爆发历史")
    treatment_success_rate: Optional[float] = Field(None, description="治疗成功率")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="历史证据置信度")

class EvidenceMatrix(BaseModel):
    """证据矩阵 - 核心数据结构"""
    visual: VisualEvidence = Field(default_factory=VisualEvidence, description="视觉证据")
    symptom: SymptomEvidence = Field(default_factory=SymptomEvidence, description="症状证据")
    environmental: EnvironmentalEvidence = Field(default_factory=EnvironmentalEvidence, description="环境证据")
    historical: HistoricalEvidence = Field(default_factory=HistoricalEvidence, description="历史证据")
    
    # 元数据
    last_updated: Optional[str] = Field(None, description="最后更新时间")
    completeness_score: float = Field(0.0, ge=0.0, le=1.0, description="证据完整性评分")
    
    def calculate_completeness(self) -> float:
        """计算证据矩阵的完整性评分"""
        total_fields = 0
        filled_fields = 0
        
        # 检查视觉证据
        visual_data = self.visual.dict()
        for key, value in visual_data.items():
            if key != 'confidence':
                total_fields += 1
                if value is not None and value != []:
                    filled_fields += 1
        
        # 检查症状证据
        symptom_data = self.symptom.dict()
        for key, value in symptom_data.items():
            if key != 'confidence':
                total_fields += 1
                if value is not None and value != []:
                    filled_fields += 1
        
        # 检查环境证据
        env_data = self.environmental.dict()
        for key, value in env_data.items():
            if key != 'confidence':
                total_fields += 1
                if value is not None and value != []:
                    filled_fields += 1
        
        # 检查历史证据
        hist_data = self.historical.dict()
        for key, value in hist_data.items():
            if key != 'confidence':
                total_fields += 1
                if value is not None and value != []:
                    filled_fields += 1
        
        if total_fields == 0:
            return 0.0
        
        self.completeness_score = filled_fields / total_fields
        return self.completeness_score

class EvidenceGap(BaseModel):
    """证据缺口结构"""
    evidence_type: EvidenceType
    field_name: str
    description: str
    importance: float = Field(ge=0.0, le=1.0, description="重要性评分")
    suggested_question: Optional[str] = Field(None, description="建议的追问")

class ConfidenceResult(BaseModel):
    """置信度计算结果"""
    disease_candidates: List[Dict[str, Any]] = Field(default_factory=list, description="候选病害列表")
    top_candidate: Optional[Dict[str, Any]] = Field(None, description="最高分候选")
    confidence_score: float = Field(0.0, ge=0.0, le=1.0, description="总体置信度")
    evidence_gaps: List[EvidenceGap] = Field(default_factory=list, description="证据缺口")
    differentiation_points: List[str] = Field(default_factory=list, description="差异化诊断点")
    reasoning: str = Field("", description="推理过程")
