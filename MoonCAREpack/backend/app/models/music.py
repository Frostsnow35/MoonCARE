from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
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


class MusicFeedback(Base):
    __tablename__ = "music_feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    music_id = Column(Integer, nullable=True, index=True)
    music_title = Column(String(200), nullable=True)
    action = Column(String(32), nullable=False, index=True)
    emotion_category = Column(String(50), nullable=True, index=True)
    source = Column(String(32), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User")

    def __repr__(self):
        return f"<MusicFeedback user={self.user_id} action={self.action}>"
