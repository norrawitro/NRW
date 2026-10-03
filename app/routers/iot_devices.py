"""NRW IoT Devices Router — อุปกรณ์ของสมาชิก (ต่อจาก iot.py เดิม ซึ่งใช้ IOT_API_KEY กลาง)

สมาชิก:  ลงทะเบียนอุปกรณ์ → ได้ device key (แสดงครั้งเดียว) · ดูค่าล่าสุด/กราฟ · ส่งคำสั่ง
ESP32:   POST /iot/device/data      (header X-Device-Key) — รูปแบบ JSON เดียวกับ /iot/data
         GET  /iot/device/commands  (header X-Device-Key) — รับคำสั่งที่ค้าง"""
import hashlib
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user
from app.models.community import IoTDevice, IoTCommand
from app.models.sensor import SensorData as Reading
from app.routers.iot import SensorData as SensorIn, UNITS
from app.services.helpers import now, fmt

router = APIRouter()


def _hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def _device_by_key(db: Session, key: str) -> IoTDevice:
    d = db.query(IoTDevice).filter(IoTDevice.key_hash == _hash(key)).first()
    if not d:
        raise HTTPException(status_code=401, detail="Invalid device key")
    return d


def _mine(db, device_id, user_id) -> IoTDevice:
    d = db.query(IoTDevice).filter(IoTDevice.device_id == device_id, IoTDevice.owner_id == user_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="ไม่พบอุปกรณ์")
    return d


# ─── ฝั่งสมาชิก ─────────────────────────────────────────────────
@router.get("/my/devices")
def my_devices(request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    out = []
    for d in db.query(IoTDevice).filter(IoTDevice.owner_id == me.id).order_by(IoTDevice.id).all():
        latest = {}
        for r in db.query(Reading).filter(Reading.device_id == d.device_id).order_by(Reading.id.desc()).limit(100).all():
            latest.setdefault(r.sensor_type, {"value": r.value, "unit": r.unit, "at": fmt(r.recorded_at)})
        out.append({"device_id": d.device_id, "name": d.name, "latest": latest})
    return {"devices": out}


class DeviceIn(BaseModel):
    device_id: str = Field(..., min_length=2, max_length=50, pattern=r"^[A-Za-z0-9_:\-]+$")
    name: str = Field(..., min_length=1, max_length=100)


@router.post("/my/devices")
def register(body: DeviceIn, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    if db.query(IoTDevice).filter(IoTDevice.device_id == body.device_id).first():
        raise HTTPException(status_code=400, detail="device_id นี้ถูกใช้แล้ว")
    key = secrets.token_urlsafe(24)
    db.add(IoTDevice(owner_id=me.id, device_id=body.device_id, name=body.name.strip(), key_hash=_hash(key)))
    db.commit()
    return {"device_id": body.device_id, "key": key}


@router.get("/my/devices/{device_id}/readings")
def readings(device_id: str, request: Request, sensor: str = "temperature", db: Session = Depends(get_db)):
    me = current_user(request, db)
    _mine(db, device_id, me.id)
    rows = (db.query(Reading).filter(Reading.device_id == device_id, Reading.sensor_type == sensor)
              .order_by(Reading.id.desc()).limit(50).all())[::-1]
    return {"sensor": sensor, "points": [{"t": fmt(r.recorded_at), "v": r.value} for r in rows]}


class CommandIn(BaseModel):
    command: str = Field(..., min_length=1, max_length=200)


@router.post("/my/devices/{device_id}/commands")
def send_command(device_id: str, body: CommandIn, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    _mine(db, device_id, me.id)
    db.add(IoTCommand(device_id=device_id, command=body.command.strip()))
    db.commit()
    return {"ok": True}


# ─── ฝั่งอุปกรณ์ (ESP32) ─────────────────────────────────────────
@router.post("/device/data")
def device_data(payload: SensorIn, db: Session = Depends(get_db), x_device_key: str = Header(...)):
    d = _device_by_key(db, x_device_key)
    if payload.device_id != d.device_id:
        raise HTTPException(status_code=403, detail="device_id ไม่ตรงกับ key")
    vals = [("temperature", payload.temperature), ("humidity", payload.humidity), ("pressure", payload.pressure)]
    vals += [(str(k)[:50], v) for k, v in (payload.custom_data or {}).items()
             if isinstance(v, (int, float)) and not isinstance(v, bool)]
    rows = [Reading(device_id=d.device_id, sensor_type=k, value=float(v), unit=UNITS.get(k, "")) for k, v in vals if v is not None]
    if not rows:
        raise HTTPException(status_code=400, detail="No sensor data provided")
    db.add_all(rows)
    db.commit()
    return {"received": True, "saved": len(rows)}


@router.get("/device/commands")
def device_commands(db: Session = Depends(get_db), x_device_key: str = Header(...)):
    d = _device_by_key(db, x_device_key)
    cmds = db.query(IoTCommand).filter(IoTCommand.device_id == d.device_id, IoTCommand.delivered_at.is_(None)).order_by(IoTCommand.id).all()
    for c in cmds:
        c.delivered_at = now()
    db.commit()
    return {"commands": [c.command for c in cmds]}
