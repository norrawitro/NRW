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
