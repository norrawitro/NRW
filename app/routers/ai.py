"""NRW AI Router — POST /ai/chat → Ollama (local) + real context from DB"""
import os
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.auth import get_current_user_from_cookie
from app.models.user import User
from app.models.wallet import Wallet
from app.models.cloud import CloudFile
from app.models.post import Post

router = APIRouter()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
# qwen3:4b-64k — สั่่่งโดย Gnoom 2026-09-30 (4b 64k context) — ใช think:false กัน thinking ปน content
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b-64k")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "300"))

SYSTEM_PROMPT = """คุณคือนอร่า (Nora) — AI ผู้ช่วยของ Nora-Web ตอบเป็นภาษาไทย สุภาพ กระชับ ลงท้ายทุกคำตอบด้วยคำว่า "จบ"
ข้อมูลปัจจุบันของผู้ใช้ (ข้อมูลจริงจากระบบ):
{context}
ตอบคำถามโดยอ้างอิงข้อมูลข้างต้น ถ้าข้อมูลไม่พอให้บอกตรงๆ ว่าไม่มีข้อมูลนั้น"""


class ChatCreate(BaseModel):
    message: str


def _require_user(request: Request, db: Session) -> User:
    payload = get_current_user_from_cookie(request)
    if not payload:
        raise HTTPException(status_code=401, detail="กรุณา login ก่อน")
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=401, detail="ไม่พบผู้ใช้")
    return user


def _build_context(db: Session, user: User) -> str:
    lines = []
    # wallet
    w = db.query(Wallet).filter(Wallet.user_id == user.id).first()
    if w:
        lines.append(f"- กระเป๋าเงิน: คงเหลือ {float(w.balance):,.2f} บาท, โทเคน {w.token} โทเคน")
    else:
        lines.append("- กระเป๋าเงิน: ยังไม่มีข้อมูล")
    # cloud storage
    total_bytes = sum(f.size or 0 for f in
                      db.query(CloudFile).filter(CloudFile.user_id == user.id).all())
    lines.append(f"- พื้นที่คลาวด์: ใช้ไป {total_bytes/1024/1024:.1f} MB จาก 50 GB")
    # latest order
    from app.models.shop import Order, ORDER_STATUS_LABELS
    o = db.query(Order).filter(Order.user_id == user.id).order_by(Order.id.desc()).first()
    if o:
        lines.append(f"- ออเดอร์ล่าสุด: #{o.id} ยอด {float(o.total):,.2f} บาท สถานะ {ORDER_STATUS_LABELS.get(o.status, o.status)}"
                     + (f" เลขพัสดุ {o.tracking}" if o.tracking else ""))
    # latest news (3 posts)
    posts = db.query(Post).filter(Post.is_deleted.is_(False)) \
        .order_by(Post.created_at.desc()).limit(3).all()
    if posts:
        lines.append("- ข่าวสารล่าสุด:")
        for p in posts:
            lines.append(f"  * [{p.created_at:%d/%m/%Y}] {p.text[:80]}")
    else:
        lines.append("- ข่าวสาร: ยังไม่มีประกาศ")
    return "\n".join(lines)


@router.post("/chat")
def ai_chat(body: ChatCreate, request: Request, db: Session = Depends(get_db)):
    user = _require_user(request, db)
    msg = body.message.strip()
    if not msg:
        raise HTTPException(status_code=400, detail="ข้อความว่าง")

    context = _build_context(db, user)
    system = SYSTEM_PROMPT.format(context=context)

    try:
        resp = httpx.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": msg},
                ],
                "stream": False,
                "think": False,
                "options": {"num_predict": 300, "temperature": 0.4},
            },
            timeout=OLLAMA_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        reply = data.get("message", {}).get("content", "").strip()
        if not reply:
            return {"reply": "ขออภัย ผมยังตอบไม่ได้ในตอนนี้ครับ", "model": OLLAMA_MODEL, "ok": False}
        # safety net: เติม "จบ" ถ้่าโมเดลลืม (กฎ shared memory)
        if not reply.rstrip().endswith("จบ"):
            reply = reply.rstrip() + " จบ"
        return {"reply": reply, "model": OLLAMA_MODEL, "ok": True}
    except httpx.ConnectError:
        return {"reply": "AI ยังไม่พร้อมใช้งาน (Ollama ไม่ออนไลน์) กรุณาลองใหม่อีกครั้งครับ", "ok": False}
    except httpx.TimeoutException:
        return {"reply": "AI ตอบช้าเกินไป ลองใหม่อีกครั้งนะครับ", "ok": False}
    except Exception:
        return {"reply": "เกิดข้อผิดพลาดในระบบ AI กรุณาลองใหม่อีกครั้งครับ", "ok": False}
