from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class BiometricData(Base):
    __tablename__ = "biometric_data"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Timestamp of the measurement
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    # Physiological signals
    hrv = Column(Float, nullable=True)  # hardware bpm -> stored as hrv
    skin_temperature = Column(Float, nullable=True)  # Celsius
    motion = Column(String(20), nullable=True)  # LOW, MEDIUM, HIGH
    cerebral_blood_flow = Column(Float, nullable=True)  # mL/100g/min, 脑血流量

    # Encrypted raw data (if needed)
    raw_data = Column(JSON, nullable=True)

    # Metadata
    device_id = Column(String(100), nullable=True)
    is_valid = Column(Integer, default=1)  # 1=valid, 0=invalid

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    user = relationship("User", back_populates="biometric_data")
