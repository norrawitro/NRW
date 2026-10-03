"""NRW Creator Router — ครีเอเตอร์/สมาชิก VIP: เปิดหน้าครีเอเตอร์ (ราคาต่อเดือน), แฟนสมัคร VIP (เงินเข้าครีเอเตอร์, 30 วัน),
โพสต์ VIP เห็นเฉพาะคนที่สมัครอยู่"""
from datetime import timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user, optional_user
from app.models.community import CreatorPage, CreatorPost, Subscription
from app.services.helpers import now, aware, fmt, names, get_or_404
from app.services.wallet_ops import move_money, to_money
from app.services.moderation import submit, hidden_ids, badge, ensure_visible
from app.services.media import set_images, images_map

router = APIRouter()
DAYS = 30


def _active_sub(db, creator_id, user_id):
    s = db.query(Subscription).filter(Subscription.creator_id == creator_id, Subscription.user_id == user_id).first()
    return s if s and aware(s.expires_at) > now() else None


@router.get("")
def list_creators(request: Request, db: Session = Depends(get_db)):
    me = optional_user(request, db)
    pages = db.query(CreatorPage).order_by(CreatorPage.id.desc()).all()
    who = names(db, [p.user_id for p in pages])
    out = []
    for p in pages:
        sub = _active_sub(db, p.id, me.id) if me else None
        out.append({"id": p.id, "name": who.get(p.user_id, "—"), "bio": p.bio, "monthly_price": float(p.monthly_price),
                    "images": images_map(db, "creator", [p.id]).get(p.id, []),
                    "fans": sum(1 for s in db.query(Subscription).filter(Subscription.creator_id == p.id).all() if aware(s.expires_at) > now()),
                    "is_mine": bool(me and me.id == p.user_id), "subscribed_until": fmt(sub.expires_at, False) if sub else None})
    return {"creators": out}


class PageIn(BaseModel):
    bio: str = Field("", max_length=2000)
    monthly_price: float = Field(..., ge=1, le=100000)
    images: list[str] = Field(default_factory=list, max_length=5)


@router.post("")
def become_creator(body: PageIn, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    p = db.query(CreatorPage).filter(CreatorPage.user_id == me.id).first()
    if p:
        p.bio, p.monthly_price = body.bio.strip(), to_money(body.monthly_price)
    else:
        p = CreatorPage(user_id=me.id, bio=body.bio.strip(), monthly_price=to_money(body.monthly_price))
        db.add(p)
    db.flush()
    set_images(db, "creator", p.id, body.images)
    db.commit()
    return {"id": p.id}


@router.post("/{page_id}/subscribe")
def subscribe(page_id: int, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    p = get_or_404(db, CreatorPage, page_id, "ไม่พบครีเอเตอร์")
    if p.user_id == me.id:
        raise HTTPException(status_code=400, detail="สมัครหน้าของตัวเองไม่ได้")
    price = Decimal(str(p.monthly_price))
    move_money(db, me.id, -price, "vip", f"สมัคร VIP {DAYS} วัน")
    move_money(db, p.user_id, price, "vip", f"รายได้สมาชิก VIP จาก @{me.username}")
    s = db.query(Subscription).filter(Subscription.creator_id == p.id, Subscription.user_id == me.id).first()
    start = max(aware(s.expires_at), now()) if s else now()      # ต่ออายุต่อจากวันหมดเดิม
    if s:
        s.expires_at = start + timedelta(days=DAYS)
    else:
        s = Subscription(creator_id=p.id, user_id=me.id, expires_at=start + timedelta(days=DAYS))
        db.add(s)
    db.commit()
    return {"until": fmt(s.expires_at, False)}


@router.get("/{page_id}/posts")
def posts(page_id: int, request: Request, db: Session = Depends(get_db)):
    me = optional_user(request, db)
    p = get_or_404(db, CreatorPage, page_id, "ไม่พบครีเอเตอร์")
    can_see = bool(me and (me.id == p.user_id or _active_sub(db, p.id, me.id)))
    is_owner = bool(me and me.id == p.user_id)
    hidden = set() if is_owner else hidden_ids(db, "creator_post")
    rows = [x for x in db.query(CreatorPost).filter(CreatorPost.creator_id == p.id).order_by(CreatorPost.id.desc()).limit(50).all() if x.id not in hidden]
    return {"can_see_vip": can_see, "posts": [{"id": x.id, "title": x.title, "vip_only": x.vip_only, "date": fmt(x.created_at),
             "mod": badge(db, "creator_post", x.id) if is_owner else None,
             "body": x.body if (can_see or not x.vip_only) else None} for x in rows]}


class PostIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    body: str = Field("", max_length=20000)
    vip_only: bool = True


@router.post("/me/posts")
def add_post(body: PostIn, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    p = db.query(CreatorPage).filter(CreatorPage.user_id == me.id).first()
    if not p:
        raise HTTPException(status_code=400, detail="เปิดหน้าครีเอเตอร์ก่อน")
    post = CreatorPost(creator_id=p.id, title=body.title.strip(), body=body.body, vip_only=body.vip_only)
    db.add(post)
    db.flush()
    status = submit(db, "creator_post", post.id, me)
    db.commit()
    return {"ok": True, "mod_status": status}
