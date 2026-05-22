from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    nickname = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    is_email_verified = Column(Boolean, default=False, nullable=False)
    password_changed_at = Column(DateTime(timezone=True), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # Device binding
    device_id = Column(String(100), nullable=True)
    is_device_connected = Column(Boolean, default=False)

    # Settings
    ai_assistant_enabled = Column(Boolean, default=True)
    notifications_enabled = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    biometric_data = relationship("BiometricData", back_populates="user", cascade="all, delete-orphan")
    menstrual_records = relationship("MenstrualRecord", back_populates="user", cascade="all, delete-orphan")
    mood_diaries = relationship("MoodDiary", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    chat_memories = relationship("ChatMemory", back_populates="user", cascade="all, delete-orphan")
