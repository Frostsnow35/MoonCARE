from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime


class MoodDiaryCreate(BaseModel):
    date: datetime
    input_type: str = "text"  # "text", "voice", "both"
    original_text: Optional[str] = None
    processed_text: Optional[str] = None
    emotion_tags: Optional[List[str]] = None
    emotion_scores: Optional[Dict[str, float]] = None
    mood_level: Optional[float] = None
    keywords: Optional[List[str]] = None


class MoodDiaryUpdate(BaseModel):
    original_text: Optional[str] = None
    emotion_tags: Optional[List[str]] = None
    emotion_scores: Optional[Dict[str, float]] = None
    mood_level: Optional[float] = None
    keywords: Optional[List[str]] = None


class MoodDiaryResponse(BaseModel):
    id: int
    date: datetime
    input_type: str
    original_text: Optional[str]
    processed_text: Optional[str]
    emotion_tags: Optional[List[str]]
    emotion_scores: Optional[Dict[str, float]]
    mood_level: Optional[float]
    keywords: Optional[List[str]]
    created_at: datetime

    class Config:
        from_attributes = True


class MoodDiaryListResponse(BaseModel):
    diaries: List[MoodDiaryResponse]
    total: int
