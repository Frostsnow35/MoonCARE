from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import date, datetime


class MenstrualRecordCreate(BaseModel):
    start_date: date
    end_date: Optional[date] = None
    flow_intensity: Optional[int] = None  # 1-5
    symptoms: Optional[List[str]] = None
    notes: Optional[str] = None

    @validator("flow_intensity")
    def validate_flow(cls, v):
        if v is not None and (v < 1 or v > 5):
            raise ValueError("flow_intensity must be between 1 and 5")
        return v

    @validator("end_date")
    def validate_end_date(cls, v, values):
        if v is not None and "start_date" in values and v < values["start_date"]:
            raise ValueError("end_date cannot be before start_date")
        return v


class MenstrualRecordResponse(BaseModel):
    id: int
    cycle_number: Optional[int]
    start_date: date
    end_date: Optional[date]
    duration: Optional[int]
    flow_intensity: Optional[int]
    symptoms: Optional[List[str]]
    predicted_next_start: Optional[date]
    prediction_confidence: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True


class CyclePredictResponse(BaseModel):
    predicted_start: date
    confidence: float
    error_range: int  # ± days
    next_period_date: date
    current_phase: str
    phase_days_remaining: int
