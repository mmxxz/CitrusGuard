import uuid
from pydantic import BaseModel, Field
from typing import List, Any

# --- Chat Message Schemas ---
class MessageBase(BaseModel):
    sender: str = Field(..., example="ai")
    content_text: str | None = Field(None)
    content_image_urls: List[str] | None = Field(None)
    message_type: str = Field("text", example="text")

class Message(MessageBase):
    id: uuid.UUID
    session_id: uuid.UUID
    timestamp: Any # Using Any for now to avoid datetime parsing issues on client

    class Config:
        from_attributes = True

# --- Diagnosis Session Schemas ---

# For starting a new session
class DiagnosisSessionStart(BaseModel):
    initial_description: str | None = Field(None, example="我的橘子树叶子发黄了")
    image_urls: List[str] | None = Field(None, example=["http://.../image.jpg"])

# For continuing a session
class DiagnosisSessionContinue(BaseModel):
    user_input: str | None = Field(None, example="主要集中在老叶片上")
    image_urls: List[str] | None = Field(None)
    # This could be expanded to include structured responses from cards
    selected_option: str | None = Field(None)

# The response from the AI
class AIResponse(BaseModel):
    type: str = Field(..., example="clarification") # text, clarification, diagnosis_result
    content: str = Field(..., example="请问是新叶还是老叶？")
    options: List[str] | None = Field(None, example=["新叶", "老叶", "都有"])

# The response when starting or continuing a session
class DiagnosisSessionResponse(BaseModel):
    session_id: uuid.UUID
    ai_response: AIResponse

class DiagnosisSessionStartResponse(BaseModel):
    session_id: str

# --- Diagnosis Result Schemas ---
class DiagnosisResultBase(BaseModel):
    primary_diagnosis: str = Field(..., example="柑橘缺镁症")
    confidence: float = Field(..., example=0.92)
    secondary_diagnoses: List[dict] = Field([], example=[{"name": "柑橘黄化病", "confidence": 0.15}])
    prevention_advice: str = Field(..., example="定期施用镁肥...")
    treatment_advice: str = Field(..., example="立即喷施硫酸镁叶面肥...")
    follow_up_plan: str = Field(..., example="7天后观察新叶生长情况并反馈效果。")
    # 与 diagnoses 表 original_image_urls 对齐，便于病例/档案展示本次上传图
    original_image_urls: List[str] = Field(default_factory=list, example=[])

class DiagnosisResultCreate(DiagnosisResultBase):
    pass # LLM will provide these fields

class DiagnosisResult(DiagnosisResultBase):
    id: uuid.UUID
    session_id: uuid.UUID
    generated_at: Any

    class Config:
        from_attributes = True

# --- Diagnosis Result Schemas ---
class DiagnosisBase(BaseModel):
    primary_diagnosis: str = Field(..., example="柑橘红蜘蛛")
    confidence: float = Field(..., example=0.85)
    secondary_diagnoses: List[dict] = Field(default_factory=list)
    prevention_advice: str = Field(..., example="加强通风透光...")
    treatment_advice: str = Field(..., example="喷施阿维菌素1000倍液...")
    follow_up_plan: str = Field(..., example="7天后观察效果...")
    
    # 新增字段：病例管理
    maintenance_advice: str | None = Field(None, example="定期检查叶片背面...")
    severity_level: str | None = Field(None, example="high")  # 'high', 'medium', 'low'
    case_status: str | None = Field(None, example="active")  # 'active', 'resolved', 'monitoring'
    last_maintenance_date: Any | None = None
    maintenance_history: List[dict] | None = Field(None, example=[{"date": "2024-01-15", "action": "喷药", "effectiveness": 8}])

class DiagnosisCreate(DiagnosisBase):
    session_id: uuid.UUID
    orchard_id: uuid.UUID
    original_image_urls: List[str] = Field(default_factory=list)

class DiagnosisUpdate(BaseModel):
    primary_diagnosis: str | None = None
    confidence: float | None = None
    secondary_diagnoses: List[dict] | None = None
    prevention_advice: str | None = None
    treatment_advice: str | None = None
    follow_up_plan: str | None = None

class DiagnosisInDBBase(DiagnosisBase):
    id: uuid.UUID
    session_id: uuid.UUID
    orchard_id: uuid.UUID
    original_image_urls: List[str]
    generated_at: Any

    class Config:
        from_attributes = True

class Diagnosis(DiagnosisInDBBase):
    pass

class DiagnosisInDB(DiagnosisInDBBase):
    pass

# --- Case File Schemas ---
class CaseFileBase(BaseModel):
    diagnosis: str = Field(..., example="柑橘红蜘蛛")
    status: str = Field(..., example="active") # "active" or "resolved"
    severity: str = Field(..., example="high") # "high", "medium", "low"
    treatment: str | None = Field(None, example="喷施阿维菌素1000倍液")
    effectiveness: int | None = Field(None, example=8) # 1-10 scale

class CaseFile(CaseFileBase):
    id: uuid.UUID
    date: Any # Using Any for now to avoid datetime parsing issues on client
    
    class Config:
        from_attributes = True

# --- Case Question Schemas ---
class CaseQuestion(BaseModel):
    question: str = Field(..., min_length=1, example="上次喷药后效果不明显，现在该怎么办？")
