from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Text, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class MenstrualRecord(Base):
    __tablename__ = "menstrual_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Cycle information
    cycle_number = Column(Integer, nullable=True)  # Cycle count from first record

    # Dates
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=True)

    # Duration
    duration = Column(Integer, nullable=True)  # days

    # Flow intensity (1-5)
    flow_intensity = Column(Integer, nullable=True)

    # Symptoms (JSON array of symptom tags)
    symptoms = Column(Text, nullable=True)  # JSON array: ["headache", "fatigue", "irritability"]

    # Notes
    notes = Column(Text, nullable=True)

    # Prediction data (populated after analysis)
    predicted_next_start = Column(Date, nullable=True)
    prediction_confidence = Column(Float, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship
    user = relationship("User", back_populates="menstrual_records")
