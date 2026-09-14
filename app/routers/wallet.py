"""NRW Wallet Router — GET /wallet, POST /wallet/tx"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.auth import get_current_user_from_cookie
from app.models.user import User
from app.models.wallet import Wallet, WalletTransaction

router = APIRouter()


class TxCreate(BaseModel):
    type: str        # topup / withdraw
    amount: float
    desc: str = ""


def _require_user(request: Request, db: Session):
    payload = get_current_user_from_cookie(request)
    if not payload:
        raise HTTPException(status_code=401, detail="กรุณา login ก่อน")
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=401, detail="ไม่พบผู้ใช้")
    return user


def _get_or_create_wallet(db: Session, user_id: int) -> Wallet:
    w = db.query(Wallet).filter(Wallet.user_id == user_id).first()
    if not w:
        w = Wallet(user_id=user_id, balance=0, token=0)
        db.add(w)
        db.flush()
    return w


# ─── GET /wallet ────────────────────────────────────────────────
@router.get("")
def get_wallet(request: Request, db: Session = Depends(get_db)):
    user = _require_user(request, db)
    w = _get_or_create_wallet(db, user.id)
    db.commit()
    txs = (
        db.query(WalletTransaction)
        .filter(WalletTransaction.user_id == user.id)
        .order_by(WalletTransaction.created_at.desc())
        .limit(50)
        .all()
    )
    return {
        "balance": float(w.balance),
        "token": w.token,
        "tx": [
            {
                "date": t.created_at.strftime("%d/%m/%Y %H:%M") if t.created_at else "—",
                "desc": t.desc,
                "amount": float(t.amount),
                "status": "สำเร็จ",
            }
            for t in txs
        ],
    }


# ─── POST /wallet/tx ────────────────────────────────────────────
@router.post("/tx")
def create_tx(body: TxCreate, request: Request, db: Session = Depends(get_db)):
    user = _require_user(request, db)
    if body.type not in ("topup", "withdraw"):
        raise HTTPException(status_code=400, detail="type ต้องเป็น topup หรือ withdraw")
    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="amount ต้องมากกว่า 0")

    w = _get_or_create_wallet(db, user.id)
    w.balance = float(w.balance or 0)

    if body.type == "topup":
        w.balance += body.amount
        desc = body.desc or "เติมเงินเข้ากระเป๋า"
    else:  # withdraw
        if w.balance < body.amount:
            raise HTTPException(status_code=400, detail="ยอดไม่พอถอน")
        w.balance -= body.amount
        desc = body.desc or "ถอนเงินออกจากกระเป๋า"

    db.add(WalletTransaction(user_id=user.id, type=body.type,
                             amount=body.amount if body.type == "topup" else -body.amount,
                             desc=desc))
    db.commit()
    return {"ok": True, "balance": float(w.balance)}
