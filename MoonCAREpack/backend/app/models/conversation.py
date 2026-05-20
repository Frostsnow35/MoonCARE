from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Session information
    session_id = Column(String(100), nullable=False, index=True)
    turn_number = Column(Integer, default=0)

    # Message content
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)

    # AI analysis (for user messages)
    intent = Column(String(50), nullable=True)  # "emotion_share", "question", "greeting"
    sentiment_score = Column(Float, nullable=True)  # -1 to 1
    is_sensitive = Column(Integer, default=0)  # 0=safe, 1=sensitive detected

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    user = relationship("User", back_populates="conversations")
