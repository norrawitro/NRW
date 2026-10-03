"""NRW DM Router — ข้อความส่วนตัว (Direct Message) แบบกล่องข้อความ: รายการบทสนทนา, ยังไม่อ่าน, แนบรูป

ใช้ตาราง chat_messages เดียวกับแชท (room = 'dm:<id เล็ก>:<id ใหญ่>') + dm_reads เก็บว่าอ่านถึงไหน
GET  /dm/inbox                     บทสนทนาทั้งหมด (ล่าสุดก่อน) + จำนวนที่ยังไม่อ่าน
GET  /dm/unread                    {"total": n} — ตัวเลขบนปุ่ม ✉️ ที่หัวเว็บ
GET  /dm/users?q=                  ค้นหาสมาชิกเพื่อเริ่มคุย
GET  /dm/with/{username}?after=    ข้อความกับคนนี้ (และบันทึกว่าอ่านแล้ว)
POST /dm/with/{username}           {text, images}  ส่งข้อความ"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user
from app.models.user import User
from app.models.work import ChatMessage, DmRead
from app.services.helpers import fmt
from app.services.media import set_images, images_map

router = APIRouter()


def dm_room(a: int, b: int) -> str:
    lo, hi = sorted([a, b])
    return f"dm:{lo}:{hi}"


def _my_rooms_filter(me_id: int):
    return or_(ChatMessage.room.like(f"dm:{me_id}:%"), ChatMessage.room.like(f"dm:%:{me_id}"))


def _other_id(room: str, me_id: int) -> int:
    a, b = map(int, room.split(":")[1:])
    return b if a == me_id else a


def _reads(db: Session, me_id: int) -> dict[str, int]:
    return {r.room: r.last_read_id for r in db.query(DmRead).filter(DmRead.user_id == me_id).all()}


def _unread(db: Session, me_id: int, room: str, last_read: int) -> int:
    return db.query(ChatMessage).filter(ChatMessage.room == room, ChatMessage.id > last_read,
                                        ChatMessage.sender_id != me_id).count()


def _user_brief(u: User) -> dict:
    name = u.full_name or u.username
    return {"username": u.username, "name": name, "initial": name[:1].upper()}


@router.get("/inbox")
def inbox(request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    last_ids = (db.query(ChatMessage.room, func.max(ChatMessage.id)).filter(_my_rooms_filter(me.id))
                  .group_by(ChatMessage.room).all())
    reads = _reads(db, me.id)
    msgs = {m.id: m for m in db.query(ChatMessage).filter(ChatMessage.id.in_([i for _, i in last_ids])).all()} if last_ids else {}
    users = {u.id: u for u in db.query(User).filter(User.id.in_([_other_id(r, me.id) for r, _ in last_ids])).all()} if last_ids else {}
    out = []
    for room, last_id in sorted(last_ids, key=lambda x: -x[1]):
        m, u = msgs.get(last_id), users.get(_other_id(room, me.id))
        if not m or not u:
            continue
        preview = m.text or "📷 รูปภาพ"
        out.append({**_user_brief(u), "last": ("คุณ: " if m.sender_id == me.id else "") + preview[:80],
                    "time": fmt(m.created_at), "unread": _unread(db, me.id, room, reads.get(room, 0))})
    return {"conversations": out, "total_unread": sum(c["unread"] for c in out)}


@router.get("/unread")
def unread(request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    reads = _reads(db, me.id)
    rooms = [r for (r,) in db.query(ChatMessage.room).filter(_my_rooms_filter(me.id)).distinct().all()]
    return {"total": sum(_unread(db, me.id, r, reads.get(r, 0)) for r in rooms)}


@router.get("/users")
def search_users(request: Request, q: str = "", db: Session = Depends(get_db)):
    me = current_user(request, db)
    q = q.strip()
    if len(q) < 1:
        return {"users": []}
    like = f"%{q}%"
    rows = (db.query(User).filter(User.id != me.id, User.is_active == True,
                                  or_(User.username.ilike(like), User.full_name.ilike(like)))
              .order_by(User.username).limit(10).all())
    return {"users": [_user_brief(u) for u in rows]}


def _other(db: Session, me: User, username: str) -> User:
    other = db.query(User).filter(User.username == username.lower(), User.is_active == True).first()
    if not other or other.id == me.id:
        raise HTTPException(status_code=404, detail="ไม่พบผู้ใช้")
    return other


@router.get("/with/{username}")
def conversation(username: str, request: Request, after: int = 0, db: Session = Depends(get_db)):
    me = current_user(request, db)
    other = _other(db, me, username)
    room = dm_room(me.id, other.id)
    rows = (db.query(ChatMessage).filter(ChatMessage.room == room, ChatMessage.id > after)
              .order_by(ChatMessage.id.desc()).limit(200).all()[::-1])
    if rows:
        r = db.query(DmRead).filter(DmRead.user_id == me.id, DmRead.room == room).first()
        if not r:
            r = DmRead(user_id=me.id, room=room, last_read_id=0)
            db.add(r)
        r.last_read_id = max(r.last_read_id or 0, rows[-1].id)
        db.commit()
    imgs = images_map(db, "dm", [m.id for m in rows])
    return {"with": _user_brief(other),
            "messages": [{"id": m.id, "text": m.text, "mine": m.sender_id == me.id, "time": fmt(m.created_at),
                          "images": imgs.get(m.id, [])} for m in rows]}


class DmIn(BaseModel):
    text: str = Field("", max_length=2000)
    images: list[str] = Field(default_factory=list, max_length=5)


@router.post("/with/{username}")
def send(username: str, body: DmIn, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    other = _other(db, me, username)
    text = body.text.strip()
    if not text and not body.images:
        raise HTTPException(status_code=400, detail="พิมพ์ข้อความหรือแนบรูปก่อนส่ง")
    m = ChatMessage(room=dm_room(me.id, other.id), sender_id=me.id, text=text)
    db.add(m)
    db.flush()
    set_images(db, "dm", m.id, body.images)
    db.commit()
    return {"id": m.id}
