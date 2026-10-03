"""NRW Chat Router — แชท: ห้องรวม (general) + คุยส่วนตัว (DM) — หน้าเว็บดึงข้อความใหม่ทุก 3 วินาที"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user
from app.models.user import User
from app.models.work import ChatMessage
from app.services.helpers import fmt, names

router = APIRouter()


def dm_room(a: int, b: int) -> str:
    lo, hi = sorted([a, b])
    return f"dm:{lo}:{hi}"


def _room_for(db: Session, me: User, room: str) -> str:
    """ตรวจสิทธิ์ห้อง — general หรือ dm:<username>"""
    if room == "general":
        return room
    if room.startswith("dm:"):
        other = db.query(User).filter(User.username == room[3:].lower(), User.is_active == True).first()
        if not other or other.id == me.id:
            raise HTTPException(status_code=404, detail="ไม่พบผู้ใช้")
        return dm_room(me.id, other.id)
    raise HTTPException(status_code=400, detail="ห้องไม่ถูกต้อง")


@router.get("/rooms")
def my_rooms(request: Request, db: Session = Depends(get_db)):
    """ห้อง DM ที่เคยคุย"""
    me = current_user(request, db)
    rows = (db.query(ChatMessage.room).filter(or_(ChatMessage.room.like(f"dm:{me.id}:%"), ChatMessage.room.like(f"dm:%:{me.id}")))
              .distinct().all())
    other_ids = []
    for (room,) in rows:
        a, b = map(int, room.split(":")[1:])
        other_ids.append(b if a == me.id else a)
    users = db.query(User).filter(User.id.in_(other_ids)).all() if other_ids else []
    return {"rooms": [{"room": "general", "label": "💬 ห้องรวม"}] +
                     [{"room": f"dm:{u.username}", "label": f"👤 {u.full_name or u.username}"} for u in users]}


@router.get("/messages")
def messages(request: Request, room: str = "general", after: int = 0, db: Session = Depends(get_db)):
    me = current_user(request, db)
    key = _room_for(db, me, room)
    q = db.query(ChatMessage).filter(ChatMessage.room == key, ChatMessage.id > after)
    rows = q.order_by(ChatMessage.id.desc()).limit(100).all()[::-1]
    who = names(db, [m.sender_id for m in rows])
    return {"messages": [{"id": m.id, "text": m.text, "sender": who.get(m.sender_id, "—"),
                          "mine": m.sender_id == me.id, "time": fmt(m.created_at)} for m in rows]}


class Send(BaseModel):
    room: str = Field("general", max_length=60)
    text: str = Field(..., min_length=1, max_length=2000)


@router.post("/messages")
def send(body: Send, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    key = _room_for(db, me, body.room)
    m = ChatMessage(room=key, sender_id=me.id, text=body.text.strip())
    db.add(m)
    db.commit()
    return {"id": m.id}
