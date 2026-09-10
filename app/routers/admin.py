"""NRW Admin Router — จัดการข้อมูล"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db

router = APIRouter()

@router.get("/")
async def admin_home():
    return {"module": "Admin", "status": "ok"}

@router.get("/dashboard")
async def dashboard(db: Session = Depends(get_db)):
    """ภาพรวมระบบ"""
    return {"users": 0, "orders": 0, "sensors": 0}
