"""NRW IoT Router — ESP32 endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.auth import verify_iot_api_key
from app.models.sensor import SensorData as SensorDataModel

router = APIRouter()


class SensorData(BaseModel):
    """Schema สำหรับข้อมูล sensor"""
    device_id: str = Field(..., min_length=1, max_length=50)
    temperature: Optional[float] = Field(None, ge=-50, le=100)
    humidity: Optional[float] = Field(None, ge=0, le=100)
    pressure: Optional[float] = Field(None, ge=0)
    custom_data: Optional[dict] = None


# หน่วยประจำ sensor type (ตรงกับ column unit ใน DB)
UNITS = {"temperature": "°C", "humidity": "%", "pressure": "hPa"}


@router.get("/ping")
async def iot_ping():
    """ESP32 health check (ไมตอง auth)"""
    return {"status": "ok", "module": "IoT", "timestamp": datetime.utcnow().isoformat()}


@router.post("/data")
async def receive_sensor_data(
    payload: SensorData,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_iot_api_key)  # ตองมี API Key
):
    """รับข้อมูล sensor จาก ESP32 (ตองมี X-API-Key header) — บันทึกลง DB sensor_data"""
    # แตก payload เปนแถว (1 แถว = 1 sensor_type) ตาม schema ของตาราง sensor_data
    readings = []
    if payload.temperature is not None:
        readings.append(("temperature", payload.temperature))
    if payload.humidity is not None:
        readings.append(("humidity", payload.humidity))
    if payload.pressure is not None:
        readings.append(("pressure", payload.pressure))
    if payload.custom_data:
        for key, value in payload.custom_data.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                readings.append((str(key)[:50], float(value)))

    if not readings:
        raise HTTPException(status_code=400, detail="No sensor data provided")

    rows = [
        SensorDataModel(
            device_id=payload.device_id,
            sensor_type=sensor_type,
            value=value,
            unit=UNITS.get(sensor_type, ""),
        )
        for sensor_type, value in readings
    ]
    db.add_all(rows)
    db.commit()

    return {
        "received": True,
        "saved": len(rows),
        "device_id": payload.device_id,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/devices")
async def list_devices(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_iot_api_key)
):
    """รายการ devices ทังหมด (distinct device_id จาก sensor_data)"""
    rows = (
        db.query(
            SensorDataModel.device_id,
            func.count(SensorDataModel.id),
            func.max(SensorDataModel.recorded_at),
        )
        .group_by(SensorDataModel.device_id)
        .order_by(SensorDataModel.device_id)
        .all()
    )
    return {
        "devices": [
            {
                "device_id": device_id,
                "reading_count": reading_count,
                "last_seen": last_seen.isoformat() if last_seen else None,
            }
            for device_id, reading_count, last_seen in rows
        ]
    }
