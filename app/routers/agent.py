"""NRW Agent Router — ควบคุม AI Agent (Hermes ใน tmux บนเครื่อง WSL) จากหน้าศูนย์ AI · ใช้ได้เฉพาะเจ้าของ

ความปลอดภัย (ส่วนนี้สั่งงานเครื่องได้จริง จึงล็อกหลายชั้น):
  1) ต้อง login เป็นผู้ดูแล (ถ้าตั้ง AGENT_OWNER=username จะใช้ได้เฉพาะบัญชีนั้นคนเดียว) — ลูกค้าได้ 403
  2) ต้องใส่รหัสผ่าน Agent แยกอีกชั้น (ตั้งด้วย `python set_agent_password.py`) — ยังไม่ตั้ง = ปิดใช้งาน
  3) ปลดล็อกแล้วอยู่ได้ AGENT_SESSION_MIN นาที (ค่าเริ่มต้น 120) · ผิด 5 ครั้งใน 15 นาที = ล็อก 15 นาที
  4) คำสั่ง POST ต้องมี header X-WKW-Agent (กันเว็บอื่นแอบสั่ง) · ส่งเข้า tmux แบบไม่ผ่าน shell

GET  /agent/state            เปิดใช้/ปลดล็อกแล้วหรือยัง + ปุ่มโมเดล
POST /agent/unlock {password} · POST /agent/lock
GET  /agent/status           CPU/RAM/GPU %, โมเดลใน Ollama (สัดส่วน CPU/GPU), tmux, หน้าจอ terminal
POST /agent/send {text} · POST /agent/model {id} · POST /agent/stop · POST /agent/reset · POST /agent/enter"""
import hashlib
import hmac
import logging
import os
import time
from collections import deque

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import SECRET_KEY
from app.database import get_db
from app.deps import current_user
from app.models.user import User
from app.services import agent_host as host

router = APIRouter()
log = logging.getLogger("wkw.agent")
COOKIE = "wkw_agent"
SESSION_MIN = int(os.getenv("AGENT_SESSION_MIN", "120"))
MAX_FAILS, FAIL_WINDOW = 5, 15 * 60
_fails: dict[str, list[float]] = {}
_history: deque = deque(maxlen=50)


def password_hash() -> str:
    return os.getenv("AGENT_PASSWORD_HASH", "")


def make_hash(password: str, salt: bytes | None = None, iterations: int = 200_000) -> str:
    salt = salt or os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${dk.hex()}"


def check_password(password: str, stored: str) -> bool:
    try:
        algo, it, salt, digest = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(it))
        return hmac.compare_digest(dk.hex(), digest)
    except (ValueError, TypeError):
        return False


def _owner(request: Request, db: Session) -> User:
    me = current_user(request, db)
    owner = os.getenv("AGENT_OWNER", "").strip().lower()
    if not me.is_admin or (owner and me.username != owner):
        raise HTTPException(status_code=403, detail="ส่วนนี้สำหรับเจ้าของระบบเท่านั้น")
    return me


def _sign(user_id: int, exp: int) -> str:
    msg = f"{user_id}.{exp}.{password_hash()[-16:]}"      # เปลี่ยนรหัส = session เก่าใช้ไม่ได้ทันที
    return hmac.new(SECRET_KEY.encode(), msg.encode(), hashlib.sha256).hexdigest()


def _session_left(request: Request, me: User) -> int:
    raw = request.cookies.get(COOKIE, "")
    try:
        uid, exp, sig = raw.split(".")
        uid, exp = int(uid), int(exp)
    except ValueError:
        return 0
    if uid != me.id or exp < time.time() or not hmac.compare_digest(sig, _sign(uid, exp)):
        return 0
    return int(exp - time.time())


def _unlocked(request: Request, db: Session) -> User:
    me = _owner(request, db)
    if not password_hash():
        raise HTTPException(status_code=403, detail="ยังไม่ได้ตั้งรหัสผ่าน Agent — รัน python set_agent_password.py")
    if _session_left(request, me) <= 0:
        raise HTTPException(status_code=401, detail="กรุณาใส่รหัสผ่าน Agent")
    if request.method == "POST" and request.headers.get("X-WKW-Agent") != "1":
        raise HTTPException(status_code=403, detail="คำขอไม่ถูกต้อง")
    return me


def _record(me: User, action: str, detail: str, ok: bool, msg: str = "") -> dict:
    item = {"time": time.strftime("%H:%M:%S"), "action": action, "detail": detail[:200], "ok": ok, "message": msg[:300]}
    _history.appendleft(item)
    log.info("agent %s by %s: %s (%s)", action, me.username, detail[:200], "ok" if ok else msg)
    if not ok:
        raise HTTPException(status_code=502, detail=f"ส่งเข้า terminal ไม่สำเร็จ: {msg or 'ไม่พบ tmux session ' + host.TMUX_TARGET}")
    return item


@router.get("/state")
def state(request: Request, db: Session = Depends(get_db)):
    me = _owner(request, db)
    left = _session_left(request, me) if password_hash() else 0
    return {"enabled": bool(password_hash()), "unlocked": left > 0, "expires_in": left,
            "target": host.TMUX_TARGET, "models": host.models(), "stop": host.STOP_CMD, "reset": host.RESET_CMD}


class UnlockIn(BaseModel):
    password: str = Field(..., min_length=1, max_length=200)


@router.post("/unlock")
def unlock(body: UnlockIn, request: Request, response: Response, db: Session = Depends(get_db)):
    me = _owner(request, db)
    if not password_hash():
        raise HTTPException(status_code=403, detail="ยังไม่ได้ตั้งรหัสผ่าน Agent — รัน python set_agent_password.py")
    key = f"{me.id}:{request.client.host if request.client else '-'}"
    now = time.time()
    fails = [t for t in _fails.get(key, []) if now - t < FAIL_WINDOW]
    if len(fails) >= MAX_FAILS:
        raise HTTPException(status_code=429, detail="ใส่รหัสผิดหลายครั้ง — ลองใหม่ใน 15 นาที")
    if not check_password(body.password, password_hash()):
        fails.append(now)
        _fails[key] = fails
        log.warning("agent unlock failed for %s (%d/%d)", me.username, len(fails), MAX_FAILS)
        raise HTTPException(status_code=401, detail=f"รหัสผ่านไม่ถูกต้อง (เหลือ {MAX_FAILS - len(fails)} ครั้ง)")
    _fails.pop(key, None)
    exp = int(now) + SESSION_MIN * 60
    response.set_cookie(COOKIE, f"{me.id}.{exp}.{_sign(me.id, exp)}", httponly=True, samesite="strict",
                        max_age=SESSION_MIN * 60, path="/agent")
    log.info("agent unlocked by %s", me.username)
    return {"unlocked": True, "expires_in": SESSION_MIN * 60}


@router.post("/lock")
def lock(request: Request, response: Response, db: Session = Depends(get_db)):
    _owner(request, db)
    response.delete_cookie(COOKIE, path="/agent")
    return {"unlocked": False}


@router.get("/status")
def status(request: Request, lines: int = 120, db: Session = Depends(get_db)):
    _unlocked(request, db)
    alive = host.tmux_alive()
    ok, screen = host.capture(max(20, min(lines, 400))) if alive else (False, "")
    gpus = host.gpu_status()
    return {"time": time.strftime("%H:%M:%S"), "cpu": host.cpu_percent(), "mem": host.mem_percent(),
            "gpus": gpus, "gpu": gpus[0]["util"] if gpus else None, "ollama": host.ollama_status(),
            "tmux": {"target": host.TMUX_TARGET, "alive": alive}, "screen": screen if ok else "",
            "history": list(_history)[:15], "expires_in": _session_left(request, _owner(request, db))}


class SendIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)


@router.post("/send")
def send(body: SendIn, request: Request, db: Session = Depends(get_db)):
    me = _unlocked(request, db)
    text = " ".join(body.text.replace("\r", "\n").split("\n")).strip()   # หลายบรรทัด → บรรทัดเดียว (Enter กลางข้อความ = ส่งก่อนเวลา)
    if not text:
        raise HTTPException(status_code=400, detail="ข้อความว่าง")
    ok, msg = host.send_text(text)
    return _record(me, "send", text, ok, msg)


class ModelIn(BaseModel):
    id: int


@router.post("/model")
def choose_model(body: ModelIn, request: Request, db: Session = Depends(get_db)):
    me = _unlocked(request, db)
    m = next((x for x in host.models() if x["id"] == body.id), None)
    if not m:
        raise HTTPException(status_code=404, detail="ไม่พบโมเดลนี้")
    ok, msg = host.send_text(m["command"])
    return _record(me, "model", f"{m['label']} → {m['command']}", ok, msg)


@router.post("/stop")
def stop(request: Request, db: Session = Depends(get_db)):
    me = _unlocked(request, db)
    ok, msg = host.send_command(host.STOP_CMD)
    return _record(me, "stop", host.STOP_CMD, ok, msg)


@router.post("/enter")
def enter(request: Request, db: Session = Depends(get_db)):
    """กด Enter อย่างเดียว — ส่งข้อความที่ค้างอยู่ในช่องพิมพ์ของ Hermes"""
    me = _unlocked(request, db)
    ok, msg = host.press("Enter")
    return _record(me, "enter", "⏎", ok, msg)


@router.post("/reset")
def reset(request: Request, db: Session = Depends(get_db)):
    me = _unlocked(request, db)
    ok, msg = host.send_command(host.RESET_CMD)
    return _record(me, "reset", host.RESET_CMD, ok, msg)
