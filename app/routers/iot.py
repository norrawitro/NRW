"""NRW IoT Router — ESP32 endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.auth import verify_iot_api_key

router = APIRouter()


class SensorData(BaseModel):
    """Schema สำหรับข้อมูล sensor"""
    device_id: str = Field(..., min_length=1, max_length=50)
    temperature: Optional[float] = Field(None, ge=-50, le=100)
    humidity: Optional[float] = Field(None, ge=0, le=100)
    pressure: Optional[float] = Field(None, ge=0)
    custom_data: Optional[dict] = None


@router.get("/ping")
async def iot_ping():
    """ESP32 health check (ไม่ต้อง auth)"""
    return {"status": "ok", "module": "IoT", "timestamp": datetime.utcnow().isoformat()}


@router.post("/data")
async def receive_sensor_data(
    payload: SensorData,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_iot_api_key)  # ต้องมี API Key
):
    """รับข้อมูล sensor จาก ESP32 (ต้องมี X-API-Key header)"""
    # TODO: บันทึก sensor data ลง DB
    return {
        "received": True,
        "device_id": payload.device_id,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/devices")
async def list_devices(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_iot_api_key)
):
    """รายการ devices ทั้งหมด"""
    # TODO: query จาก DB
    return {"devices": []}
