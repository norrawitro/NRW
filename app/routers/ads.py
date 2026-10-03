"""NRW Ads Router — โฆษณา: สมาชิกซื้อพื้นที่โฆษณา (AD_PRICE_PER_DAY บาท/วัน, ค่าเริ่มต้น 20)
โฆษณาที่ยังไม่หมดอายุจะสุ่มแสดงบนหน้าแรก · นับการแสดงผล/คลิก · ผู้ดูแลปิดโฆษณาที่ไม่เหมาะสมได้"""
import os
import random
from datetime import timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user, current_admin
from app.models.work import Ad
from app.services.helpers import now, aware, fmt, safe_link, get_or_404, names
from app.services.wallet_ops import move_money

router = APIRouter()
PRICE_PER_DAY = Decimal(os.getenv("AD_PRICE_PER_DAY", "20"))


def ad_dict(a, owner=None):
    d = {"id": a.id, "title": a.title, "text": a.text, "has_link": bool(a.link), "views": a.views, "clicks": a.clicks,
         "ends": fmt(a.ends_at), "running": a.is_active and aware(a.ends_at) > now(), "is_active": a.is_active,
         "paid": float(a.paid)}
    if owner is not None:
        d["owner"] = owner
    return d


@router.get("/serve")
def serve(db: Session = Depends(get_db)):
    """สุ่ม 1 โฆษณาที่กำลังแสดงอยู่ (หน้าแรกเรียก)"""
    live = [a for a in db.query(Ad).filter(Ad.is_active == True).all() if aware(a.ends_at) > now()]
    if not live:
        return {"ad": None}
    a = random.choice(live)
    a.views += 1
    db.commit()
    return {"ad": {"id": a.id, "title": a.title, "text": a.text, "has_link": bool(a.link)}}


@router.get("/{ad_id}/go")
def click(ad_id: int, db: Session = Depends(get_db)):
    a = get_or_404(db, Ad, ad_id, "ไม่พบโฆษณา")
    if not a.link:
        raise HTTPException(status_code=404, detail="โฆษณานี้ไม่มีลิงก์")
    a.clicks += 1
    db.commit()
    return RedirectResponse(a.link, status_code=302)


@router.get("")
def my_ads(request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    return {"price_per_day": float(PRICE_PER_DAY),
            "ads": [ad_dict(a) for a in db.query(Ad).filter(Ad.owner_id == me.id).order_by(Ad.id.desc()).all()]}


class AdIn(BaseModel):
    title: str = Field(..., min_length=2, max_length=100)
    text: str = Field("", max_length=300)
    link: str = Field("", max_length=500)
    days: int = Field(..., ge=1, le=90)


@router.post("")
def buy_ad(body: AdIn, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    link = safe_link(body.link)
    cost = PRICE_PER_DAY * body.days
    move_money(db, me.id, -cost, "ads", f"ซื้อโฆษณา {body.days} วัน: {body.title}")
    a = Ad(owner_id=me.id, title=body.title.strip(), text=body.text.strip(), link=link, paid=cost,
           ends_at=now() + timedelta(days=body.days))
    db.add(a)
    db.commit()
    return ad_dict(a)


@router.get("/admin/all")
def all_ads(request: Request, db: Session = Depends(get_db)):
    current_admin(request, db)
    ads = db.query(Ad).order_by(Ad.id.desc()).limit(200).all()
    who = names(db, [a.owner_id for a in ads])
    return {"ads": [ad_dict(a, who.get(a.owner_id, "—")) for a in ads]}


@router.post("/{ad_id}/toggle")
def toggle(ad_id: int, request: Request, db: Session = Depends(get_db)):
    current_admin(request, db)
    a = get_or_404(db, Ad, ad_id, "ไม่พบโฆษณา")
    a.is_active = not a.is_active
    db.commit()
    return ad_dict(a)
