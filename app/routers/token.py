"""NRW Token Router — สินทรัพย์ดิจิทัล/โทเคน

ได้โทเคนจากการซื้อสินค้า (ดู shop.py) — โอนให้สมาชิกอื่น หรือแลกเป็นเงินเข้ากระเป๋า
อัตราแลก: TOKEN_REDEEM_RATE โทเคน = 1 บาท (ค่าเริ่มต้น 10)
"""
import os
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user
from app.models.user import User
from app.models.wallet import TokenTransaction
from app.services.wallet_ops import get_wallet, move_tokens, move_money

router = APIRouter()
REDEEM_RATE = int(os.getenv("TOKEN_REDEEM_RATE", "10"))
KIND_LABELS = {"earn": "ได้จากการซื้อ", "transfer_in": "รับโอน", "transfer_out": "โอนออก",
               "redeem": "แลกเป็นเงิน", "admin": "ปรับโดยผู้ดูแล"}


@router.get("")
def my_tokens(request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    w = get_wallet(db, me.id)
    db.commit()
    txs = (db.query(TokenTransaction).filter(TokenTransaction.user_id == me.id)
             .order_by(TokenTransaction.id.desc()).limit(50).all())
    return {"token": int(w.token or 0), "redeem_rate": REDEEM_RATE,
            "history": [{"amount": t.amount, "kind": t.kind, "label": KIND_LABELS.get(t.kind, t.kind),
                         "note": t.note, "date": t.created_at.strftime("%d/%m/%Y %H:%M") if t.created_at else "—"}
                        for t in txs]}


class Transfer(BaseModel):
    to_username: str = Field(..., min_length=3, max_length=50)
    amount: int = Field(..., ge=1, le=10_000_000)


@router.post("/transfer")
def transfer(body: Transfer, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    to = db.query(User).filter(User.username == body.to_username.strip().lower(), User.is_active == True).first()
    if not to:
        raise HTTPException(status_code=404, detail="ไม่พบผู้รับ")
    if to.id == me.id:
        raise HTTPException(status_code=400, detail="โอนให้ตัวเองไม่ได้")
    # ล็อกตามลำดับ id กัน deadlock เมื่อโอนหากันพร้อมกัน
    first, second = sorted([me.id, to.id])
    get_wallet(db, first, lock=True); get_wallet(db, second, lock=True)
    move_tokens(db, me.id, -body.amount, "transfer_out", f"โอนให้ @{to.username}")
    move_tokens(db, to.id, body.amount, "transfer_in", f"รับจาก @{me.username}")
    db.commit()
    return {"token": int(get_wallet(db, me.id).token or 0)}


class Redeem(BaseModel):
    amount: int = Field(..., ge=1, le=10_000_000)


@router.post("/redeem")
def redeem(body: Redeem, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    if REDEEM_RATE <= 0 or body.amount % REDEEM_RATE:
        raise HTTPException(status_code=400, detail=f"แลกได้ทีละ {REDEEM_RATE} โทเคน")
    baht = Decimal(body.amount // REDEEM_RATE)
    move_tokens(db, me.id, -body.amount, "redeem", f"แลกเป็นเงิน ฿{baht:,.0f}")
    move_money(db, me.id, baht, "token_redeem", f"แลกจาก {body.amount:,} โทเคน")
    db.commit()
    w = get_wallet(db, me.id)
    return {"token": int(w.token or 0), "balance": float(w.balance or 0)}


# ─── ตลาดโทเคน: ประกาศซื้อ / ประกาศขาย ───────────────────────────
from app.models.wallet import TokenOffer
from app.services.helpers import names, fmt
from app.services.wallet_ops import to_money

OFFER_SIDES = {"sell": "ขาย", "buy": "ซื้อ"}


def offer_dict(o: TokenOffer, who: dict, me) -> dict:
    return {"id": o.id, "side": o.side, "side_label": OFFER_SIDES[o.side], "price": float(o.price),
            "amount": o.amount, "remaining": o.remaining, "status": o.status, "owner": who.get(o.user_id, "—"),
            "is_mine": bool(me and me.id == o.user_id), "date": fmt(o.created_at)}


@router.get("/offers")
def list_offers(request: Request, mine: bool = False, db: Session = Depends(get_db)):
    """ประกาศที่เปิดอยู่ — ขายเรียงราคาถูกก่อน, ซื้อเรียงราคาสูงก่อน"""
    me = current_user(request, db)
    q = db.query(TokenOffer)
    q = q.filter(TokenOffer.user_id == me.id) if mine else q.filter(TokenOffer.status == "open")
    rows = q.order_by(TokenOffer.id.desc()).limit(200).all()
    who = names(db, [o.user_id for o in rows])
    sells = sorted([o for o in rows if o.side == "sell"], key=lambda o: o.price)
    buys = sorted([o for o in rows if o.side == "buy"], key=lambda o: -o.price)
    return {"sell": [offer_dict(o, who, me) for o in sells], "buy": [offer_dict(o, who, me) for o in buys]}


class OfferIn(BaseModel):
    side: str = Field(..., pattern="^(sell|buy)$")
    amount: int = Field(..., ge=1, le=10_000_000)
    price: float = Field(..., gt=0, le=1_000_000)       # บาท/โทเคน


@router.post("/offers")
def create_offer(body: OfferIn, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    price = to_money(body.price)
    if price <= 0:
        raise HTTPException(status_code=400, detail="ราคาต้องมากกว่า 0")
    o = TokenOffer(user_id=me.id, side=body.side, price=price, amount=body.amount, remaining=body.amount, status="open")
    db.add(o)
    db.flush()
    if body.side == "sell":
        move_tokens(db, me.id, -body.amount, "transfer_out", f"พักโทเคนสำหรับประกาศขาย #{o.id}")
    else:
        move_money(db, me.id, -(price * body.amount), "token_offer", f"พักเงินสำหรับประกาศซื้อโทเคน #{o.id}")
    db.commit()
    return offer_dict(o, names(db, [me.id]), me)


class TakeIn(BaseModel):
    amount: int = Field(..., ge=1, le=10_000_000)


@router.post("/offers/{offer_id}/take")
def take_offer(offer_id: int, body: TakeIn, request: Request, db: Session = Depends(get_db)):
    """รับประกาศ — ซื้อจากประกาศขาย หรือ ขายให้ประกาศซื้อ (รับบางส่วนได้)"""
    me = current_user(request, db)
    o = db.query(TokenOffer).filter(TokenOffer.id == offer_id).with_for_update().first()
    if not o or o.status != "open":
        raise HTTPException(status_code=404, detail="ประกาศนี้ปิดแล้ว")
    if o.user_id == me.id:
        raise HTTPException(status_code=400, detail="รับประกาศของตัวเองไม่ได้")
    if body.amount > o.remaining:
        raise HTTPException(status_code=400, detail=f"ประกาศนี้เหลือ {o.remaining:,} โทเคน")
    total = Decimal(str(o.price)) * body.amount
    if o.side == "sell":        # ฉันซื้อ: จ่ายเงินให้ผู้ขาย, รับโทเคนที่พักไว้
        move_money(db, me.id, -total, "token_trade", f"ซื้อ {body.amount:,} โทเคน (ประกาศ #{o.id})")
        move_money(db, o.user_id, total, "token_trade", f"ขาย {body.amount:,} โทเคน (ประกาศ #{o.id})")
        move_tokens(db, me.id, body.amount, "transfer_in", f"ซื้อจากประกาศ #{o.id}")
    else:                       # ฉันขาย: ให้โทเคนผู้ซื้อ, รับเงินที่พักไว้
        move_tokens(db, me.id, -body.amount, "transfer_out", f"ขายให้ประกาศซื้อ #{o.id}")
        move_tokens(db, o.user_id, body.amount, "transfer_in", f"ได้จากประกาศซื้อ #{o.id}")
        move_money(db, me.id, total, "token_trade", f"ขาย {body.amount:,} โทเคน (ประกาศ #{o.id})")
    o.remaining -= body.amount
    if o.remaining == 0:
        o.status = "filled"
    db.commit()
    return {"total": float(total), "remaining": o.remaining}


@router.post("/offers/{offer_id}/cancel")
def cancel_offer(offer_id: int, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    o = db.query(TokenOffer).filter(TokenOffer.id == offer_id, TokenOffer.user_id == me.id).with_for_update().first()
    if not o or o.status != "open":
        raise HTTPException(status_code=404, detail="ไม่พบประกาศที่เปิดอยู่ของคุณ")
    if o.remaining:
        if o.side == "sell":
            move_tokens(db, me.id, o.remaining, "transfer_in", f"คืนโทเคน ยกเลิกประกาศ #{o.id}")
        else:
            move_money(db, me.id, Decimal(str(o.price)) * o.remaining, "refund", f"คืนเงิน ยกเลิกประกาศซื้อ #{o.id}")
    o.status = "cancelled"
    db.commit()
    return {"ok": True}
