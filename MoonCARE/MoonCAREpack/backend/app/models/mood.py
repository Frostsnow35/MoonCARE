from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class MoodDiary(Base):
    __tablename__ = "mood_diaries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Date and time
    date = Column(DateTime(timezone=True), nullable=False, index=True)

    # Input type: "text", "voice", or "both"
    input_type = Column(String(20), default="text")

    # Content
    original_text = Column(Text, nullable=True)  # Original input (may be voice transcript)
    processed_text = Column(Text, nullable=True)  # NLP processed

    # Emotion analysis results
    emotion_tags = Column(JSON, nullable=True)  # ["anxious", "low", "calm"]
    emotion_scores = Column(JSON, nullable=True)  # {"anxiety": 0.7, "sadness": 0.3}
    mood_level = Column(Float, nullable=True)  # 1-10 scale

    # Keywords extracted
    keywords = Column(JSON, nullable=True)  # ["烦躁", "失眠"]

    # Related data
    menstrual_record_id = Column(Integer, ForeignKey("menstrual_records.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship
    user = relationship("User", back_populates="mood_diaries")
