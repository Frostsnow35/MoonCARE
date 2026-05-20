from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class AssessmentSession(Base):
    """Hidden non-questionnaire premenstrual state assessment session."""

    __tablename__ = "assessment_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    chat_session_id = Column(String(100), nullable=False, index=True)
    status = Column(String(40), nullable=False, default="idle")
    trigger_source = Column(String(60), nullable=False, default="chat")
    current_dimension = Column(String(60), nullable=True)
    asked_dimensions = Column(JSON, nullable=False, default=list)
    cooldown_until = Column(DateTime(timezone=True), nullable=True)
    summary_level = Column(String(60), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    observations = relationship(
        "AssessmentObservation",
        back_populates="assessment_session",
        cascade="all, delete-orphan",
    )


class AssessmentObservation(Base):
    """Structured signal extracted from a natural chat answer."""

    __tablename__ = "assessment_observations"

    id = Column(Integer, primary_key=True, index=True)
    assessment_session_id = Column(Integer, ForeignKey("assessment_sessions.id"), nullable=False, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True, index=True)
    dimension = Column(String(60), nullable=False)
    value = Column(JSON, nullable=False, default=dict)
    confidence = Column(Float, nullable=False, default=0.0)
    evidence_text = Column(Text, nullable=False, default="")
    crisis_signal = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    assessment_session = relationship("AssessmentSession", back_populates="observations")
