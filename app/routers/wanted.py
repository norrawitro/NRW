"""NRW Wanted Router — ประกาศซื้อ: โพสต์ว่าต้องการซื้ออะไร (รูป + ข้อความ + งบ), คนมีของยื่นข้อเสนอ,
เจ้าของประกาศกด "รับข้อเสนอ" → จ่ายเงินจากกระเป๋าให้ผู้ขายทันที แล้วประกาศปิดเป็น "ได้ของแล้ว"

GET  /wanted/posts?mine=          รายการประกาศ (ที่เปิดอยู่ / ของฉัน)
POST /wanted/posts                {title, description, budget, images}
POST /wanted/posts/{id}/close     เจ้าของปิดประกาศ
GET  /wanted/posts/{id}/offers    เจ้าของเห็นทุกข้อเสนอ, คนอื่นเห็นเฉพาะของตัวเอง
POST /wanted/posts/{id}/offers    {message, price}  ยื่นข้อเสนอ (ของตัวเองไม่ได้)
POST /wanted/offers/{id}/accept   เจ้าของรับข้อเสนอ → จ่ายเงิน
POST /wanted/offers/{id}/decline  เจ้าของปฏิเสธ"""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user, optional_user
from app.models.user import User
from app.models.wanted import WantedPost, WantedOffer
from app.services.helpers import fmt, names
from app.services.wallet_ops import move_money, to_money
from app.services.moderation import submit, hidden_ids, badge, ensure_visible
from app.services.media import set_images, images_map

router = APIRouter()
STATUS_LABELS = {"open": "กำลังหา", "done": "ได้ของแล้ว", "closed": "ปิดแล้ว"}
OFFER_LABELS = {"pending": "รอตอบ", "accepted": "รับแล้ว", "declined": "ไม่รับ"}


def post_dicts(db: Session, rows: list[WantedPost], me: User | None) -> list[dict]:
    ids = [p.id for p in rows]
    who = names(db, [p.user_id for p in rows])
    imgs = images_map(db, "wanted", ids)
    counts = {}
    for o in db.query(WantedOffer.post_id).filter(WantedOffer.post_id.in_(ids)).all() if ids else []:
        counts[o.post_id] = counts.get(o.post_id, 0) + 1
    out = []
    for p in rows:
        mine = bool(me and me.id == p.user_id)
        out.append({"id": p.id, "title": p.title, "description": p.description, "budget": float(p.budget),
                    "status": p.status, "status_label": STATUS_LABELS.get(p.status, p.status),
                    "buyer": who.get(p.user_id, "—"), "is_mine": mine, "date": fmt(p.created_at, False),
                    "images": imgs.get(p.id, []), "offer_count": counts.get(p.id, 0),
                    "mod": badge(db, "wanted", p.id) if mine else None})
    return out


@router.get("/posts")
def list_posts(request: Request, mine: bool = False, db: Session = Depends(get_db)):
    me = optional_user(request, db)
    q = db.query(WantedPost)
    if mine:
        if not me:
            raise HTTPException(status_code=401, detail="กรุณา login ก่อน")
        q = q.filter(WantedPost.user_id == me.id)
    else:
        q = q.filter(WantedPost.status == "open")
    hidden = set() if mine else hidden_ids(db, "wanted")
    rows = [p for p in q.order_by(WantedPost.id.desc()).limit(100).all() if p.id not in hidden]
    return {"posts": post_dicts(db, rows, me)}


class PostIn(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: str = Field("", max_length=3000)
    budget: float = Field(..., gt=0, le=10_000_000)
    images: list[str] = Field(default_factory=list, max_length=5)


@router.post("/posts")
def create_post(body: PostIn, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    p = WantedPost(user_id=me.id, title=body.title.strip(), description=body.description.strip(),
                   budget=to_money(body.budget), status="open")
    db.add(p)
    db.flush()
    set_images(db, "wanted", p.id, body.images)
    status = submit(db, "wanted", p.id, me)
    db.commit()
    return {**post_dicts(db, [p], me)[0], "mod_status": status}


def _my_post(db: Session, post_id: int, me: User) -> WantedPost:
    p = db.query(WantedPost).filter(WantedPost.id == post_id, WantedPost.user_id == me.id).with_for_update().first()
    if not p:
        raise HTTPException(status_code=404, detail="ไม่พบประกาศของคุณ")
    return p


@router.post("/posts/{post_id}/close")
def close_post(post_id: int, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    p = _my_post(db, post_id, me)
    if p.status != "open":
        raise HTTPException(status_code=400, detail="ประกาศนี้ปิดไปแล้ว")
    p.status = "closed"
    db.query(WantedOffer).filter(WantedOffer.post_id == p.id, WantedOffer.status == "pending").update({"status": "declined"})
    db.commit()
    return post_dicts(db, [p], me)[0]


@router.get("/posts/{post_id}/offers")
def list_offers(post_id: int, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    p = db.query(WantedPost).filter(WantedPost.id == post_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="ไม่พบประกาศ")
    q = db.query(WantedOffer).filter(WantedOffer.post_id == p.id)
    if p.user_id != me.id:
        q = q.filter(WantedOffer.seller_id == me.id)
    rows = q.order_by(WantedOffer.price, WantedOffer.id).all()
    who = names(db, [o.seller_id for o in rows])
    imgs = images_map(db, "wanted_offer", [o.id for o in rows])
    return {"is_owner": p.user_id == me.id, "post_status": p.status,
            "offers": [{"id": o.id, "seller": who.get(o.seller_id, "—"), "message": o.message, "price": float(o.price),
                        "status": o.status, "status_label": OFFER_LABELS.get(o.status, o.status),
                        "is_mine": o.seller_id == me.id, "date": fmt(o.created_at),
                        "images": imgs.get(o.id, [])} for o in rows]}


class OfferIn(BaseModel):
    message: str = Field("", max_length=2000)
    price: float = Field(..., gt=0, le=10_000_000)
    images: list[str] = Field(default_factory=list, max_length=5)


@router.post("/posts/{post_id}/offers")
def make_offer(post_id: int, body: OfferIn, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    p = db.query(WantedPost).filter(WantedPost.id == post_id).first()
    if not p or p.status != "open":
        raise HTTPException(status_code=404, detail="ประกาศนี้ไม่เปิดรับข้อเสนอแล้ว")
    if p.user_id == me.id:
        raise HTTPException(status_code=400, detail="ยื่นข้อเสนอให้ประกาศของตัวเองไม่ได้")
    ensure_visible(db, "wanted", p.id, p.user_id, None, "ประกาศนี้")
    if db.query(WantedOffer).filter(WantedOffer.post_id == p.id, WantedOffer.seller_id == me.id,
                                    WantedOffer.status == "pending").count() >= 3:
        raise HTTPException(status_code=400, detail="ยื่นข้อเสนอที่รอตอบได้สูงสุด 3 รายการต่อประกาศ")
    o = WantedOffer(post_id=p.id, seller_id=me.id, message=body.message.strip(), price=to_money(body.price))
    db.add(o)
    db.flush()
    set_images(db, "wanted_offer", o.id, body.images)
    db.commit()
    return {"id": o.id, "price": float(o.price), "status": o.status}


def _owner_offer(db: Session, offer_id: int, me: User) -> tuple[WantedOffer, WantedPost]:
    o = db.query(WantedOffer).filter(WantedOffer.id == offer_id).with_for_update().first()
    p = db.query(WantedPost).filter(WantedPost.id == o.post_id).with_for_update().first() if o else None
    if not o or not p or p.user_id != me.id:
        raise HTTPException(status_code=404, detail="ไม่พบข้อเสนอในประกาศของคุณ")
    if o.status != "pending" or p.status != "open":
        raise HTTPException(status_code=400, detail="ข้อเสนอนี้ตอบไปแล้ว หรือประกาศปิดแล้ว")
    return o, p


@router.post("/offers/{offer_id}/accept")
def accept_offer(offer_id: int, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    o, p = _owner_offer(db, offer_id, me)
    total = Decimal(str(o.price))
    move_money(db, me.id, -total, "wanted", f"ซื้อตามประกาศ: {p.title}")
    move_money(db, o.seller_id, total, "wanted", f"ขายตามประกาศซื้อ: {p.title}")
    o.status, p.status = "accepted", "done"
    db.query(WantedOffer).filter(WantedOffer.post_id == p.id, WantedOffer.id != o.id,
                                 WantedOffer.status == "pending").update({"status": "declined"})
    db.commit()
    return {"ok": True, "total": float(total)}


@router.post("/offers/{offer_id}/decline")
def decline_offer(offer_id: int, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    o, _ = _owner_offer(db, offer_id, me)
    o.status = "declined"
    db.commit()
    return {"ok": True}
