"""NRW helpers ที่หลายระบบใช้ร่วมกัน"""
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.user import User


def now() -> datetime:
    return datetime.now(timezone.utc)


def aware(dt: datetime | None) -> datetime | None:
    """SQLite คืนเวลาแบบไม่มี timezone — ถือว่าเป็น UTC"""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def fmt(dt: datetime | None, with_time: bool = True) -> str:
    if not dt:
        return "—"
    return dt.strftime("%d/%m/%Y %H:%M" if with_time else "%d/%m/%Y")


def names(db: Session, ids) -> dict[int, str]:
    """{user_id: ชื่อ} ทีเดียวหลายคน"""
    ids = {i for i in ids if i}
    if not ids:
        return {}
    return {u.id: u.full_name or u.username for u in db.query(User).filter(User.id.in_(ids)).all()}


def get_or_404(db: Session, model, obj_id: int, msg: str = "ไม่พบข้อมูล", lock: bool = False):
    q = db.query(model).filter(model.id == obj_id)
    if lock:
        q = q.with_for_update()
    obj = q.first()
    if not obj:
        raise HTTPException(status_code=404, detail=msg)
    return obj


def safe_link(url: str) -> str:
    """อนุญาตเฉพาะลิงก์ http(s) — กัน javascript: ฯลฯ"""
    url = (url or "").strip()
    if url and not url.lower().startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="ลิงก์ต้องขึ้นต้นด้วย http:// หรือ https://")
    return url
