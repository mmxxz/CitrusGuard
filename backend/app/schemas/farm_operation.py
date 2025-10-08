import uuid
from pydantic import BaseModel, Field
from datetime import date
from typing import List

class FarmOperationBase(BaseModel):
    type: str = Field(..., example="spraying")
    description: str | None = Field(None, example="Foliar spray of magnesium sulfate")
    materials_used: List[str] = Field([], example=["magnesium sulfate", "water"])
    operation_date: date

class FarmOperationCreate(FarmOperationBase):
    diagnosis_id: uuid.UUID | None = None

class FarmOperationUpdate(FarmOperationBase):
    pass

class FarmOperationInDBBase(FarmOperationBase):
    id: uuid.UUID
    orchard_id: uuid.UUID
    user_id: uuid.UUID

    class Config:
        from_attributes = True

class FarmOperation(FarmOperationInDBBase):
    pass

class FarmOperationInDB(FarmOperationInDBBase):
    pass
