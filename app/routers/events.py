"""NRW Events Router — กิจกรรม/สัมมนา/ตั๋ว: สร้างกิจกรรม, ซื้อตั๋ว (เงินเข้าผู้จัด), รหัสตั๋ว, เช็คอินหน้างาน"""
import secrets
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user, optional_user
from app.models.community import Event, Ticket
from app.services.helpers import now, aware, fmt, names, get_or_404
from app.services.wallet_ops import move_money, to_money

router = APIRouter()


def event_dict(db, e, me, who):
    sold = db.query(Ticket).filter(Ticket.event_id == e.id).count()
    mine = db.query(Ticket).filter(Ticket.event_id == e.id, Ticket.user_id == me.id).first() if me else None
    return {"id": e.id, "title": e.title, "description": e.description, "when": fmt(e.starts_at), "place": e.place,
            "price": float(e.price), "capacity": e.capacity, "sold": sold, "organizer": who.get(e.organizer_id, "—"),
            "is_mine": bool(me and me.id == e.organizer_id), "past": aware(e.starts_at) < now(),
            "my_ticket": mine.code if mine else None}


@router.get("")
def list_events(request: Request, db: Session = Depends(get_db)):
    me = optional_user(request, db)
    evs = db.query(Event).order_by(Event.starts_at.desc()).limit(100).all()
    who = names(db, [e.organizer_id for e in evs])
    return {"events": [event_dict(db, e, me, who) for e in evs]}


class EventIn(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field("", max_length=5000)
    starts_at: datetime
    place: str = Field("", max_length=300)
    price: float = Field(0, ge=0, le=1_000_000)
    capacity: int = Field(50, ge=1, le=100000)


@router.post("")
def create_event(body: EventIn, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    e = Event(organizer_id=me.id, title=body.title.strip(), description=body.description.strip(),
              starts_at=body.starts_at, place=body.place.strip(), price=to_money(body.price), capacity=body.capacity)
    db.add(e)
    db.commit()
    return {"id": e.id}


@router.post("/{event_id}/tickets")
def buy_ticket(event_id: int, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    e = get_or_404(db, Event, event_id, "ไม่พบกิจกรรม", lock=True)
    if aware(e.starts_at) < now():
        raise HTTPException(status_code=400, detail="กิจกรรมผ่านไปแล้ว")
    if db.query(Ticket).filter(Ticket.event_id == e.id, Ticket.user_id == me.id).first():
        raise HTTPException(status_code=400, detail="มีตั๋วแล้ว")
    if db.query(Ticket).filter(Ticket.event_id == e.id).count() >= e.capacity:
        raise HTTPException(status_code=400, detail="ตั๋วเต็มแล้ว")
    price = Decimal(str(e.price))
    if price > 0 and e.organizer_id != me.id:
        move_money(db, me.id, -price, "ticket", f"ตั๋ว: {e.title}")
        move_money(db, e.organizer_id, price, "ticket", f"ขายตั๋ว: {e.title}")
    t = Ticket(event_id=e.id, user_id=me.id, code=secrets.token_hex(4).upper())
    db.add(t)
    db.commit()
    return {"code": t.code}


@router.get("/{event_id}/attendees")
def attendees(event_id: int, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    e = get_or_404(db, Event, event_id, "ไม่พบกิจกรรม")
    if e.organizer_id != me.id:
        raise HTTPException(status_code=403, detail="เฉพาะผู้จัด")
    ts = db.query(Ticket).filter(Ticket.event_id == e.id).order_by(Ticket.id).all()
    who = names(db, [t.user_id for t in ts])
    return {"attendees": [{"name": who.get(t.user_id, "—"), "code": t.code, "checked_in": fmt(t.checked_in_at) if t.checked_in_at else None} for t in ts]}


class CheckIn(BaseModel):
    code: str = Field(..., min_length=4, max_length=12)


@router.post("/{event_id}/checkin")
def check_in(event_id: int, body: CheckIn, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    e = get_or_404(db, Event, event_id, "ไม่พบกิจกรรม")
    if e.organizer_id != me.id:
        raise HTTPException(status_code=403, detail="เฉพาะผู้จัด")
    t = db.query(Ticket).filter(Ticket.event_id == e.id, Ticket.code == body.code.strip().upper()).first()
    if not t:
        raise HTTPException(status_code=404, detail="รหัสตั๋วไม่ถูกต้อง")
    if t.checked_in_at:
        raise HTTPException(status_code=400, detail=f"เช็คอินไปแล้วเมื่อ {fmt(t.checked_in_at)}")
    t.checked_in_at = now()
    db.commit()
    return {"name": names(db, [t.user_id]).get(t.user_id, "—")}
