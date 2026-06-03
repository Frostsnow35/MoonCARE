from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr
    nickname: Optional[str] = None
    phone: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    nickname: Optional[str] = None
    phone: Optional[str] = None
    device_id: Optional[str] = None
    ai_assistant_enabled: Optional[bool] = None
    notifications_enabled: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    device_id: Optional[str] = None
    is_device_connected: bool
    ai_assistant_enabled: bool
    notifications_enabled: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
