"""NRW Sensor model — ESP32 / IoT data"""
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from app.database import Base

class SensorData(Base):
    __tablename__ = "sensor_data"

    id          = Column(Integer, primary_key=True, index=True)
    device_id   = Column(String(50), nullable=False, index=True)  # ESP32 MAC/name
    sensor_type = Column(String(50), nullable=False)               # temp, humidity, etc.
    value       = Column(Float, nullable=False)
    unit        = Column(String(20), default="")
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
