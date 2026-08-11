from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ChatMemory(Base):
    """Persistent, minimal user memory extracted from safe chat turns."""

    __tablename__ = "chat_memories"
    __table_args__ = (
        UniqueConstraint("user_id", "category", "key", name="uq_chat_memory_user_category_key"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    source_conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True, index=True)
    category = Column(String(40), nullable=False, index=True)
    key = Column(String(80), nullable=False)
    value = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False, default=0.6)
    source = Column(String(40), nullable=False, default="chat")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    user = relationship("User", back_populates="chat_memories")
