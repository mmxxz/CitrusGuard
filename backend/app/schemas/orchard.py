import uuid
from pydantic import BaseModel, Field
from datetime import date

# Shared properties
class OrchardBase(BaseModel):
    name: str = Field(..., example="王先生的阳光果园")
    location_latitude: float | None = Field(None, example=30.6578)
    location_longitude: float | None = Field(None, example=104.0658)
    address_detail: str | None = Field(None, example="四川省成都市武侯区")
    main_variety: str | None = Field(None, example="不知火柑")
    avg_tree_age: int | None = Field(None, example=5)
    soil_type: str | None = Field(None, example="沙壤土")
    last_harvest_date: date | None = Field(None)

# Properties to receive on creation
class OrchardCreate(OrchardBase):
    pass

# Properties to receive on update
class OrchardUpdate(OrchardBase):
    pass

# Properties shared by models stored in DB
class OrchardInDBBase(OrchardBase):
    id: uuid.UUID
    user_id: uuid.UUID

    class Config:
        from_attributes = True

# Properties to return to client
class Orchard(OrchardInDBBase):
    pass

# Additional properties stored in DB
class OrchardInDB(OrchardInDBBase):
    pass
