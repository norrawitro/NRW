"""NRW IoT Router — ESP32 endpoints"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db

router = APIRouter()

@router.get("/ping")
async def iot_ping():
    """ESP32 health check"""
    return {"status": "ok", "module": "IoT"}

@router.post("/data")
async def receive_sensor_data(payload: dict, db: Session = Depends(get_db)):
    """รับข้อมูล sensor จาก ESP32"""
    # TODO: บันทึก sensor data ลง DB
    return {"received": True, "data": payload}
