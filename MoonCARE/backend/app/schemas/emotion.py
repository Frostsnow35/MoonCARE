from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime


class EmotionPredictRequest(BaseModel):
    user_id: int
    days: int = 7  # prediction horizon


class EmotionPredictResponse(BaseModel):
    phase: str  # "follicular", "ovulation", "luteal", "menstrual", "unknown"
    pms_risk: float  # 0.0 - 1.0
    mood_level: float  # 1.0 - 10.0
    confidence: float  # 0.0 - 1.0
    updated_at: datetime


class InterventionRecommendResponse(BaseModel):
    recommendations: List[str]  # ["breathing_exercise", "music_therapy", "walking"]
    reasons: Dict[str, str]
    priority: str  # "low", "medium", "high"


class EmotionAnalysisResult(BaseModel):
    emotion_tags: List[str]
    emotion_scores: Dict[str, float]
    mood_level: float
    keywords: List[str]
    confidence: float
