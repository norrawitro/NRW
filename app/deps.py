"""NRW shared dependencies — ดึงผู้ใช้ที่ login อยู่ (ใช้ร่วมกันทุก router)"""
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.auth import get_current_user_from_cookie
from app.models.user import User


def optional_user(request: Request, db: Session) -> User | None:
    """คืน User ถ้า login อยู่ (และบัญชียังใช้งานได้) ไม่งั้นคืน None"""
    payload = get_current_user_from_cookie(request)
    if not payload:
        return None
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    return user if user and user.is_active else None


def current_user(request: Request, db: Session) -> User:
    """ต้อง login — ไม่ได้ login = 401"""
    user = optional_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="กรุณา login ก่อน")
    return user


def current_admin(request: Request, db: Session) -> User:
    """ต้องเป็นผู้ดูแล (เช็ค is_admin จากฐานข้อมูล ไม่เชื่อ token อย่างเดียว)"""
    user = current_user(request, db)
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="เฉพาะผู้ดูแลระบบ")
    return user
