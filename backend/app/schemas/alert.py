import uuid
from pydantic import BaseModel, Field
from datetime import datetime

# Shared properties
class AlertBase(BaseModel):
    type: str = Field(..., example="病害")
    risk_item: str = Field(..., example="溃疡病")
    risk_level: str = Field(..., example="high")
    confidence: float = Field(..., example=0.85)
    reason: str = Field(..., example="基于未来72小时高温高湿天气预报")
    status: str = Field("active", example="active")

# Properties to receive on creation (if any, likely system-generated)
class AlertCreate(AlertBase):
    pass

# Properties to receive via API on update
class AlertUpdate(BaseModel):
    status: str = Field(..., example="ignored")

# Properties shared by models stored in DB
class AlertInDBBase(AlertBase):
    id: uuid.UUID
    orchard_id: uuid.UUID
    generated_at: datetime

    class Config:
        from_attributes = True

# Properties to return to client
class Alert(AlertInDBBase):
    pass

# Additional properties stored in DB
class AlertInDB(AlertInDBBase):
    pass
