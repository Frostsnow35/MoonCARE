from sqlalchemy import Column, Integer, String, Float, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class Music(Base):
    __tablename__ = "music"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    artist = Column(String(100), nullable=True)
    url = Column(String(500), nullable=False)
    duration = Column(Integer, nullable=True)  # seconds

    # Emotion tags for matching
    mood_tags = Column(JSON, nullable=True)  # ["happy", "sad", "anxious", "relaxed"]
    emotion_category = Column(String(50), nullable=False)  # "joy", "sadness", "anxiety", "calm"

    # Metadata
    cover_url = Column(String(500), nullable=True)
    is_active = Column(Integer, default=1)

    def __repr__(self):
        return f"<Music {self.title}>"