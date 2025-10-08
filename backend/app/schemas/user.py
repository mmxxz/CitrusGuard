from pydantic import BaseModel, EmailStr, Field
import uuid

# Shared properties
class UserBase(BaseModel):
    email: EmailStr = Field(..., example="user@example.com")
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(None, example="John Doe")

# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(..., min_length=8, example="strongpassword123")

# Properties to receive via API on update
class UserUpdate(UserBase):
    password: str | None = Field(None, min_length=8, example="newstrongpassword123")

# Properties shared by models stored in DB
class UserInDBBase(UserBase):
    id: uuid.UUID
    hashed_password: str

    class Config:
        from_attributes = True

# Properties to return to client
class User(UserBase):
    id: uuid.UUID

    class Config:
        from_attributes = True

# Additional properties stored in DB
class UserInDB(UserInDBBase):
    pass

# Schema for Token
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: str | None = None
