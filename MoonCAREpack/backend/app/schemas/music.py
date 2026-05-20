from pydantic import BaseModel
from typing import Optional, List


class Music(BaseModel):
    id: int
    title: str
    artist: Optional[str] = None
    url: str
    duration: Optional[int] = None
    mood_tags: List[str] = []
    emotion_category: str
    cover_url: Optional[str] = None

    class Config:
        from_attributes = True


class MusicRecommendRequest(BaseModel):
    user_id: int
    emotion_category: Optional[str] = None  # "joy", "sadness", "anxiety", "calm", "normal"
    mood_level: Optional[float] = None  # 1-10


class MusicRecommendResponse(BaseModel):
    current_emotion: str
    recommended_songs: List[Music]
    message: str