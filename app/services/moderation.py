"""NRW moderation — ระบบอนุมัติเนื้อหา (ใช้ร่วมกันทุกระบบที่สมาชิกลงเนื้อหาได้)

วิธีใช้ในแต่ละ router:
  ตอนสร้าง:   submit(db, "product", p.id, me)            → สมาชิกทั่วไป = รออนุมัติ, ผู้ดูแล = อนุมัติทันที
  ตอนแสดง:    hidden = hidden_ids(db, "product")         → ตัดชิ้นที่ยังไม่อนุมัติออก (ยกเว้นของเจ้าของเอง)
  ตอนซื้อ/ใช้: ensure_visible(db, "product", id, me)     → ยังไม่อนุมัติ = 404
  ป้ายให้เจ้าของ: badge(db, "product", id)                → {"status","reason"} หรือ None
ปิดระบบอนุมัติทั้งหมดได้ด้วย MODERATION=off ใน .env
"""
import os

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.moderation import Moderation
from app.services.helpers import now

ENABLED = os.getenv("MODERATION", "on").lower() not in ("off", "0", "false", "no")

LABELS = {"post": "📰 โพสต์ข่าวสาร", "product": "🛒 สินค้า", "listing": "♻️ ประกาศมือสอง", "course": "🎓 คอร์สเรียน",
          "job": "💼 งานฟรีแลนซ์", "ad": "📢 โฆษณา", "video": "🎥 วิดีโอ", "event": "🎫 กิจกรรม",
          "creator_post": "⭐ โพสต์ครีเอเตอร์", "health": "🏃 หลักฐานออกกำลังกาย"}


def submit(db: Session, kind: str, item_id: int, user) -> str:
    """บันทึกเข้าคิว (หรือส่งกลับเข้าคิวใหม่เมื่อแก้ไข) — คืนสถานะ"""
    status = "approved" if (user.is_admin or not ENABLED) else "pending"
    m = db.query(Moderation).filter(Moderation.kind == kind, Moderation.item_id == item_id).first()
    if m:
        m.status, m.reason, m.decided_by, m.decided_at = status, "", None, None
    else:
        db.add(Moderation(kind=kind, item_id=item_id, owner_id=user.id, status=status))
    return status


def hidden_ids(db: Session, kind: str) -> set[int]:
    return {m.item_id for m in db.query(Moderation.item_id).filter(Moderation.kind == kind, Moderation.status != "approved").all()}


def badge(db: Session, kind: str, item_id: int) -> dict | None:
    m = db.query(Moderation).filter(Moderation.kind == kind, Moderation.item_id == item_id).first()
    if not m or m.status == "approved":
        return None
    return {"status": m.status, "reason": m.reason}


def is_visible(db: Session, kind: str, item_id: int, owner_id: int | None, viewer=None) -> bool:
    if viewer and (viewer.is_admin or viewer.id == owner_id):
        return True
    return item_id not in hidden_ids(db, kind)


def ensure_visible(db: Session, kind: str, item_id: int, owner_id: int | None, viewer=None, msg: str = "ไม่พบข้อมูล"):
    if not is_visible(db, kind, item_id, owner_id, viewer):
        raise HTTPException(status_code=404, detail=f"{msg} (รอผู้ดูแลอนุมัติ)")


def decide(db: Session, m: Moderation, approve: bool, admin_name: str, reason: str = "") -> None:
    m.status = "approved" if approve else "rejected"
    m.reason = "" if approve else reason.strip()[:300]
    m.decided_by, m.decided_at = admin_name, now()
