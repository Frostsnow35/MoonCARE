from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class BiometricUpload(BaseModel):
    device_id: Optional[str] = "DEVICE_001"  # 硬件设备ID
    timestamp: Optional[datetime] = None  # 硬件时间戳，不提供则使用服务器时间
    bpm: Optional[float] = None  # hardware bpm -> stored as hrv
    temp: Optional[float] = None  # skin temperature
    motion: Optional[str] = None  # motion level: LOW, MEDIUM, HIGH
    confidence: Optional[str] = "HIGH"  # confidence level: LOW, HIGH
    wearing: Optional[bool] = None  # 是否佩戴
    cerebral_blood_flow: Optional[float] = None  # mL/100g/min, 脑血流量


class BiometricResponse(BaseModel):
    status: str
    msg: str
    data_id: Optional[int] = None


class BiometricQuery(BaseModel):
    user_id: int
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = 100


class BiometricDataPoint(BaseModel):
    id: int
    timestamp: datetime
    hrv: Optional[float] = None  # hardware bpm
    skin_temperature: Optional[float] = None
    motion: Optional[str] = None
    cerebral_blood_flow: Optional[float] = None  # mL/100g/min, 脑血流量

    class Config:
        from_attributes = True
