"""NRW Health Router — สุขภาพ/ออกกำลังกาย

บันทึกกิจกรรม **ต้องแนบรูปหลักฐาน** → รอผู้ดูแลอนุมัติ (/manage) → อนุมัติแล้วจึงได้โทเคน
โทเคน: 1 ต่อการออกกำลังกาย 30 นาที (นับเฉพาะรายการที่อนุมัติแล้ว) สูงสุด HEALTH_DAILY_TOKENS ต่อวัน (ค่าเริ่มต้น 5)
มีกราฟ 7 วัน และคำแนะนำจาก AI (Ollama)"""
import os
import uuid
from datetime import date, timedelta

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user
from app.models.community import HealthLog, HealthEvidence
from app.models.moderation import Moderation
from app.routers.ai import OLLAMA_URL, OLLAMA_MODEL
from app.routers.cloud import UPLOAD_ROOT
from app.services.moderation import submit
from app.services.wallet_ops import move_tokens

router = APIRouter()
DAILY_TOKENS = int(os.getenv("HEALTH_DAILY_TOKENS", "5"))
ACTIVITIES = ["เดิน", "วิ่ง", "ปั่นจักรยาน", "ว่ายน้ำ", "เวท", "โยคะ", "อื่น ๆ"]
IMAGE_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".heic": "image/heic"}
IMAGE_MAX = 8 * 1024 * 1024
STATUS_LABELS = {"pending": "⏳ รออนุมัติ", "approved": "✅ อนุมัติแล้ว", "rejected": "❌ ไม่อนุมัติ"}


def _status(db, log_id) -> tuple[str, str]:
    m = db.query(Moderation).filter(Moderation.kind == "health", Moderation.item_id == log_id).first()
    return (m.status, m.reason) if m else ("approved", "")


def _week(db, user_id):
    start = date.today() - timedelta(days=6)
    logs = db.query(HealthLog).filter(HealthLog.user_id == user_id, HealthLog.day >= start).order_by(HealthLog.id.desc()).all()
    days = [{"day": (start + timedelta(days=i)).strftime("%d/%m"), "minutes": 0, "steps": 0} for i in range(7)]
    for l in logs:
        if _status(db, l.id)[0] != "approved":
            continue                                   # กราฟนับเฉพาะที่อนุมัติแล้ว
        i = (l.day - start).days
        if 0 <= i < 7:
            days[i]["minutes"] += l.minutes
            days[i]["steps"] += l.steps
    return logs, days


def award_tokens(db: Session, log: HealthLog) -> int:
    """เรียกตอนผู้ดูแลอนุมัติ — คิดโทเคนจากนาทีที่อนุมัติแล้วของวันนั้น (ไม่เกินเพดานรายวัน)"""
    same_day = db.query(HealthLog).filter(HealthLog.user_id == log.user_id, HealthLog.day == log.day).all()
    approved = [l for l in same_day if l.id == log.id or _status(db, l.id)[0] == "approved"]
    minutes = sum(l.minutes for l in approved)
    already = sum(l.tokens for l in same_day)
    tokens = max(0, min(minutes // 30, DAILY_TOKENS) - already)
    if tokens:
        log.tokens = tokens
        move_tokens(db, log.user_id, tokens, "earn", f"ออกกำลังกาย {log.day:%d/%m} (อนุมัติแล้ว)")
    return tokens


@router.get("")
def summary(request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    logs, days = _week(db, me.id)
    out = []
    for l in logs[:20]:
        st, reason = _status(db, l.id)
        out.append({"id": l.id, "day": l.day.strftime("%d/%m"), "activity": l.activity, "minutes": l.minutes, "steps": l.steps,
                    "tokens": l.tokens, "status": st, "status_label": STATUS_LABELS[st], "reason": reason,
                    "has_evidence": db.query(HealthEvidence).filter(HealthEvidence.log_id == l.id).first() is not None})
    return {"activities": ACTIVITIES, "days": days, "daily_tokens": DAILY_TOKENS,
            "total_minutes": sum(d["minutes"] for d in days), "total_steps": sum(d["steps"] for d in days), "logs": out}


@router.post("")
async def add_log(request: Request, activity: str = Form(...), minutes: int = Form(0), steps: int = Form(0),
                  file: UploadFile = File(...), db: Session = Depends(get_db)):
    """บันทึกกิจกรรม + รูปหลักฐาน (บังคับ) → รอผู้ดูแลอนุมัติ"""
    me = current_user(request, db)
    if not (0 <= minutes <= 600 and 0 <= steps <= 100000) or (minutes == 0 and steps == 0):
        raise HTTPException(status_code=400, detail="ใส่นาที (0–600) หรือจำนวนก้าว")
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="ต้องแนบรูปหลักฐาน (jpg, png, webp, heic)")
    data = await file.read(IMAGE_MAX + 1)
    if not data:
        raise HTTPException(status_code=400, detail="ต้องแนบรูปหลักฐาน")
    if len(data) > IMAGE_MAX:
        raise HTTPException(status_code=413, detail="รูปใหญ่เกิน 8MB")
    folder = os.path.join(UPLOAD_ROOT, "health")
    os.makedirs(folder, exist_ok=True)
    rel = os.path.join("health", f"{uuid.uuid4().hex}{ext}")
    with open(os.path.join(UPLOAD_ROOT, rel), "wb") as out:
        out.write(data)
    log = HealthLog(user_id=me.id, day=date.today(), activity=(activity.strip() or "อื่น ๆ")[:50],
                    minutes=minutes, steps=steps, tokens=0)
    db.add(log)
    db.flush()
    db.add(HealthEvidence(log_id=log.id, path=rel))
    status = submit(db, "health", log.id, me)
    tokens = award_tokens(db, log) if status == "approved" else 0      # ผู้ดูแล/ปิดระบบอนุมัติ = ได้ทันที
    db.commit()
    return {"id": log.id, "status": status, "tokens": tokens}


@router.get("/evidence/{log_id}")
def evidence(log_id: int, request: Request, db: Session = Depends(get_db)):
    """ดูรูปหลักฐาน — เจ้าของหรือผู้ดูแลเท่านั้น"""
    me = current_user(request, db)
    log = db.query(HealthLog).filter(HealthLog.id == log_id).first()
    ev = db.query(HealthEvidence).filter(HealthEvidence.log_id == log_id).first()
    if not log or not ev or (log.user_id != me.id and not me.is_admin):
        raise HTTPException(status_code=404, detail="ไม่พบรูป")
    path = os.path.join(UPLOAD_ROOT, ev.path)
    if not os.path.isfile(path):
        raise HTTPException(status_code=410, detail="ไฟล์หายไป")
    return FileResponse(path, media_type=IMAGE_TYPES.get(os.path.splitext(path)[1], "image/jpeg"))


@router.get("/tip")
def tip(request: Request, db: Session = Depends(get_db)):
    """คำแนะนำจาก AI ตามสรุป 7 วัน (ถ้า Ollama ไม่พร้อม → คำแนะนำพื้นฐาน)"""
    me = current_user(request, db)
    _, days = _week(db, me.id)
    total = sum(d["minutes"] for d in days)
    fallback = ("สัปดาห์นี้ยังไม่มีการออกกำลังกายที่อนุมัติ ลองเริ่มเดินวันละ 20–30 นาทีดูนะครับ" if total == 0 else
                f"สัปดาห์นี้ออกกำลังกายรวม {total} นาที" + (" เยี่ยมมาก! ถึงเป้า 150 นาที/สัปดาห์แล้ว" if total >= 150 else
                f" อีก {150 - total} นาทีจะถึงเป้า 150 นาที/สัปดาห์ (คำแนะนำ WHO)"))
    summary_text = ", ".join(f"{d['day']}: {d['minutes']} นาที {d['steps']} ก้าว" for d in days)
    try:
        r = httpx.post(f"{OLLAMA_URL}/api/chat", timeout=60, json={
            "model": OLLAMA_MODEL, "stream": False, "think": False, "options": {"num_predict": 150, "temperature": 0.5},
            "messages": [{"role": "system", "content": "คุณคือโค้ชสุขภาพ ตอบภาษาไทย สั้นไม่เกิน 3 ประโยค ให้กำลังใจและแนะนำ 1 อย่างที่ทำได้จริง ไม่วินิจฉัยโรค"},
                         {"role": "user", "content": f"กิจกรรม 7 วันล่าสุดของฉัน: {summary_text}"}]})
        r.raise_for_status()
        text = r.json().get("message", {}).get("content", "").strip()
        return {"tip": text or fallback, "ai": bool(text)}
    except Exception:
        return {"tip": fallback, "ai": False}
