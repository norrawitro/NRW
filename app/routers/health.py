"""NRW Health Router — สุขภาพ/ออกกำลังกาย: บันทึกกิจกรรม, สรุป 7 วัน, คำแนะนำจาก AI (Ollama), แลกคะแนนเป็นโทเคน
ได้ 1 โทเคนต่อการออกกำลังกาย 30 นาที สูงสุด HEALTH_DAILY_TOKENS ต่อวัน (ค่าเริ่มต้น 5)"""
import os
from datetime import date, timedelta

import httpx
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user
from app.models.community import HealthLog
from app.routers.ai import OLLAMA_URL, OLLAMA_MODEL
from app.services.wallet_ops import move_tokens

router = APIRouter()
DAILY_TOKENS = int(os.getenv("HEALTH_DAILY_TOKENS", "5"))
ACTIVITIES = ["เดิน", "วิ่ง", "ปั่นจักรยาน", "ว่ายน้ำ", "เวท", "โยคะ", "อื่น ๆ"]


def _week(db, user_id):
    start = date.today() - timedelta(days=6)
    logs = db.query(HealthLog).filter(HealthLog.user_id == user_id, HealthLog.day >= start).order_by(HealthLog.id.desc()).all()
    days = [{"day": (start + timedelta(days=i)).strftime("%d/%m"), "minutes": 0, "steps": 0} for i in range(7)]
    for l in logs:
        i = (l.day - start).days
        if 0 <= i < 7:
            days[i]["minutes"] += l.minutes
            days[i]["steps"] += l.steps
    return logs, days


@router.get("")
def summary(request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    logs, days = _week(db, me.id)
    return {"activities": ACTIVITIES, "days": days,
            "total_minutes": sum(d["minutes"] for d in days), "total_steps": sum(d["steps"] for d in days),
            "logs": [{"day": l.day.strftime("%d/%m"), "activity": l.activity, "minutes": l.minutes, "steps": l.steps,
                      "tokens": l.tokens} for l in logs[:20]]}


class LogIn(BaseModel):
    activity: str = Field(..., max_length=50)
    minutes: int = Field(0, ge=0, le=600)
    steps: int = Field(0, ge=0, le=100000)


@router.post("")
def add_log(body: LogIn, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    today = date.today()
    earned_today = sum(l.tokens for l in db.query(HealthLog).filter(HealthLog.user_id == me.id, HealthLog.day == today).all())
    minutes_today = sum(l.minutes for l in db.query(HealthLog).filter(HealthLog.user_id == me.id, HealthLog.day == today).all())
    tokens = min((minutes_today + body.minutes) // 30, DAILY_TOKENS) - earned_today
    tokens = max(0, tokens)
    db.add(HealthLog(user_id=me.id, day=today, activity=body.activity.strip() or "อื่น ๆ",
                     minutes=body.minutes, steps=body.steps, tokens=tokens))
    if tokens:
        move_tokens(db, me.id, tokens, "earn", f"ออกกำลังกาย {body.minutes} นาที")
    db.commit()
    return {"tokens": tokens}


@router.get("/tip")
def tip(request: Request, db: Session = Depends(get_db)):
    """คำแนะนำจาก AI ตามสรุป 7 วัน (ถ้า Ollama ไม่พร้อม → คำแนะนำพื้นฐาน)"""
    me = current_user(request, db)
    _, days = _week(db, me.id)
    total = sum(d["minutes"] for d in days)
    fallback = ("สัปดาห์นี้ยังไม่ได้ออกกำลังกาย ลองเริ่มเดินวันละ 20–30 นาทีดูนะครับ" if total == 0 else
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
