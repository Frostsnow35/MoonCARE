from typing import List, Optional

from pydantic import BaseModel, Field


class Music(BaseModel):
    id: int
    title: str
    artist: Optional[str] = None
    url: str
    duration: Optional[int] = None
    mood_tags: List[str] = Field(default_factory=list)
    emotion_category: str
    cover_url: Optional[str] = None
    source: Optional[str] = "library"
    recommendation_reason: Optional[str] = None
    playback_notice: Optional[str] = None

    class Config:
        from_attributes = True


class MusicRecommendRequest(BaseModel):
    emotion_category: Optional[str] = None
    mood_level: Optional[float] = None


class MusicRecommendationContext(BaseModel):
    source: str
    reason: str
    signals: List[str] = Field(default_factory=list)
    fallback_used: bool = False
    safety_note: str = "音乐疗愈仅供参考，不能替代专业医疗或心理支持。"
    playback_notice: str = "如果浏览器阻止自动播放，请手动点击播放；如果音频不可用，可以切换下一首。"


class MusicRecommendResponse(BaseModel):
    current_emotion: str
    recommended_songs: List[Music]
    message: str
    recommendation_context: MusicRecommendationContext


class MusicFeedbackRequest(BaseModel):
    music_id: Optional[int] = None
    music_title: Optional[str] = None
    action: str
    emotion_category: Optional[str] = None
    source: Optional[str] = None
    note: Optional[str] = None


class MusicFeedbackResponse(BaseModel):
    id: int
    action: str
    music_id: Optional[int] = None
    music_title: Optional[str] = None
    source: Optional[str] = None

    class Config:
        from_attributes = True
