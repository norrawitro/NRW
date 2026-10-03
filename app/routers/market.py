"""NRW Market Router — มือสอง/เช่า: สมาชิกลงประกาศขายหรือให้เช่า, คนอื่นซื้อ/เช่าด้วยกระเป๋าเงิน

เงินโอนจากผู้ซื้อไปผู้ขายทันที (ในรายการเดียวกัน)
เช่า: ผู้ให้เช่ากด "ได้ของคืนแล้ว" → ประกาศกลับมาให้เช่าได้อีก
"""
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user, optional_user
from app.models.user import User
from app.models.market import Listing, Deal
from app.services.wallet_ops import move_money, to_money
from app.services.moderation import submit, hidden_ids, badge, ensure_visible
from app.services.media import set_images, images_map

router = APIRouter()
STATUS_LABELS = {"active": "เปิดอยู่", "sold": "ขายแล้ว", "rented": "ถูกเช่าอยู่", "closed": "ปิดแล้ว"}


def listing_dict(db: Session, l: Listing, me: User | None) -> dict:
    seller = db.query(User).filter(User.id == l.seller_id).first()
    d = {"id": l.id, "kind": l.kind, "title": l.title, "description": l.description,
         "price": float(l.price), "status": l.status, "status_label": STATUS_LABELS.get(l.status, l.status),
         "seller": seller.full_name if seller else "—", "seller_username": seller.username if seller else None, "is_mine": bool(me and me.id == l.seller_id),
         "date": l.created_at.strftime("%d/%m/%Y") if l.created_at else "—",
         "images": images_map(db, "listing", [l.id]).get(l.id, []),
         "mod": badge(db, "listing", l.id) if (me and me.id == l.seller_id) else None}
    if l.status == "rented":
        deal = (db.query(Deal).filter(Deal.listing_id == l.id, Deal.returned_at.is_(None))
                  .order_by(Deal.id.desc()).first())
        d["open_deal_id"] = deal.id if deal else None
    return d


@router.get("/listings")
def list_listings(request: Request, mine: bool = False, db: Session = Depends(get_db)):
    me = optional_user(request, db)
    q = db.query(Listing)
    if mine:
        if not me:
            raise HTTPException(status_code=401, detail="กรุณา login ก่อน")
        q = q.filter(Listing.seller_id == me.id)
    else:
        q = q.filter(Listing.status == "active")
    hidden = set() if mine else hidden_ids(db, "listing")
    rows = [l for l in q.order_by(Listing.id.desc()).limit(100).all() if l.id not in hidden]
    return {"listings": [listing_dict(db, l, me) for l in rows]}


class ListingIn(BaseModel):
    kind: str = Field(..., pattern="^(sale|rent)$")
    title: str = Field(..., min_length=2, max_length=200)
    description: str = Field("", max_length=3000)
    price: float = Field(..., gt=0, le=10_000_000)
    images: list[str] = Field(default_factory=list, max_length=5)


@router.post("/listings")
def create_listing(body: ListingIn, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    l = Listing(seller_id=me.id, kind=body.kind, title=body.title.strip(),
                description=body.description.strip(), price=to_money(body.price), status="active")
    db.add(l)
    db.flush()
    set_images(db, "listing", l.id, body.images)
    submit(db, "listing", l.id, me)
    db.commit()
    db.refresh(l)
    return listing_dict(db, l, me)


@router.post("/listings/{listing_id}/close")
def close_listing(listing_id: int, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    l = db.query(Listing).filter(Listing.id == listing_id, Listing.seller_id == me.id).first()
    if not l:
        raise HTTPException(status_code=404, detail="ไม่พบประกาศของคุณ")
    if l.status != "active":
        raise HTTPException(status_code=400, detail="ปิดได้เฉพาะประกาศที่เปิดอยู่")
    l.status = "closed"
    db.commit()
    return listing_dict(db, l, me)


class DealIn(BaseModel):
    days: int = Field(1, ge=1, le=365)    # ใช้กับการเช่าเท่านั้น


@router.post("/listings/{listing_id}/deal")
def make_deal(listing_id: int, body: DealIn, request: Request, db: Session = Depends(get_db)):
    """ซื้อ (sale) หรือเช่า (rent) — จ่ายเงินให้ผู้ขายทันที"""
    me = current_user(request, db)
    l = db.query(Listing).filter(Listing.id == listing_id).with_for_update().first()
    if not l or l.status != "active":
        raise HTTPException(status_code=404, detail="ประกาศนี้ไม่เปิดแล้ว")
    if l.seller_id == me.id:
        raise HTTPException(status_code=400, detail="ซื้อ/เช่าของตัวเองไม่ได้")
    ensure_visible(db, "listing", l.id, l.seller_id, None, "ประกาศนี้")
    days = body.days if l.kind == "rent" else 0
    total = Decimal(str(l.price)) * (days if l.kind == "rent" else 1)
    action = f"เช่า {days} วัน" if l.kind == "rent" else "ซื้อ"
    move_money(db, me.id, -total, "market", f"{action}: {l.title}")
    move_money(db, l.seller_id, total, "market", f"ได้รับเงินจาก{action}: {l.title}")
    deal = Deal(listing_id=l.id, buyer_id=me.id, kind=l.kind, days=days, total=total)
    db.add(deal)
    l.status = "rented" if l.kind == "rent" else "sold"
    db.commit()
    return {"deal_id": deal.id, "total": float(total), "listing": listing_dict(db, l, me)}


@router.post("/deals/{deal_id}/return")
def mark_returned(deal_id: int, request: Request, db: Session = Depends(get_db)):
    """ผู้ให้เช่ายืนยันว่าได้ของคืนแล้ว → เปิดให้เช่าอีกครั้ง"""
    me = current_user(request, db)
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    l = db.query(Listing).filter(Listing.id == deal.listing_id).first() if deal else None
    if not deal or not l or l.seller_id != me.id or deal.kind != "rent":
        raise HTTPException(status_code=404, detail="ไม่พบรายการเช่าของคุณ")
    if deal.returned_at:
        raise HTTPException(status_code=400, detail="บันทึกคืนของไปแล้ว")
    deal.returned_at = datetime.now(timezone.utc)
    l.status = "active"
    db.commit()
    return listing_dict(db, l, me)


@router.get("/deals")
def my_deals(request: Request, db: Session = Depends(get_db)):
    """สิ่งที่ฉันซื้อ/เช่า"""
    me = current_user(request, db)
    rows = (db.query(Deal, Listing).join(Listing, Listing.id == Deal.listing_id)
              .filter(Deal.buyer_id == me.id).order_by(Deal.id.desc()).limit(50).all())
    return {"deals": [{"id": d.id, "kind": d.kind, "title": l.title, "days": d.days, "total": float(d.total),
                       "returned": bool(d.returned_at),
                       "date": d.created_at.strftime("%d/%m/%Y") if d.created_at else "—"} for d, l in rows]}
