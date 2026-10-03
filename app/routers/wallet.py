"""NRW Wallet Router — GET /wallet, POST /wallet/tx (ส่งคำขอเติม/ถอน)

เติม/ถอนเงินต้องให้ผู้ดูแลอนุมัติที่ /manage (ยังไม่มี payment gateway):
- เติมเงิน: สร้างคำขอ → อนุมัติแล้วยอดเพิ่ม
- ถอนเงิน: กันยอดไว้ทันที → อนุมัติ = โอนจริงแล้ว / ปฏิเสธ = คืนยอดอัตโนมัติ
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import get_db
from app.deps import current_user
from app.models.wallet import WalletTransaction, WalletRequest
from app.services.wallet_ops import get_wallet, move_money, to_money

router = APIRouter()

STATUS_LABELS = {"pending": "รออนุมัติ", "approved": "สำเร็จ", "rejected": "ถูกปฏิเสธ"}
MAX_AMOUNT = 1_000_000


class TxCreate(BaseModel):
    type: str                                   # topup / withdraw
    amount: float
    desc: str = Field("", max_length=200)


def request_dict(r: WalletRequest) -> dict:
    return {"id": r.id, "type": r.type, "amount": float(r.amount), "desc": r.desc,
            "status": r.status, "status_label": STATUS_LABELS.get(r.status, r.status),
            "date": r.created_at.strftime("%d/%m/%Y %H:%M") if r.created_at else "—"}


# ─── GET /wallet ────────────────────────────────────────────────
@router.get("")
def get_my_wallet(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    w = get_wallet(db, user.id)
    db.commit()
    txs = (db.query(WalletTransaction).filter(WalletTransaction.user_id == user.id)
             .order_by(WalletTransaction.created_at.desc(), WalletTransaction.id.desc()).limit(50).all())
    reqs = (db.query(WalletRequest).filter(WalletRequest.user_id == user.id)
              .order_by(WalletRequest.id.desc()).limit(20).all())
    return {
        "balance": float(w.balance or 0),
        "token": int(w.token or 0),
        "tx": [{"date": t.created_at.strftime("%d/%m/%Y %H:%M") if t.created_at else "—",
                "desc": t.desc, "amount": float(t.amount), "status": "สำเร็จ"} for t in txs],
        "requests": [request_dict(r) for r in reqs],
    }


# ─── POST /wallet/tx — ส่งคำขอเติม/ถอน ─────────────────────────
@router.post("/tx")
def create_tx(body: TxCreate, request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if body.type not in ("topup", "withdraw"):
        raise HTTPException(status_code=400, detail="type ต้องเป็น topup หรือ withdraw")
    amount = to_money(body.amount)
    if amount <= 0 or amount > MAX_AMOUNT:
        raise HTTPException(status_code=400, detail=f"amount ต้องมากกว่า 0 และไม่เกิน {MAX_AMOUNT:,}")
    desc = body.desc.strip() or ("เติมเงินเข้ากระเป๋า" if body.type == "topup" else "ถอนเงินออกจากกระเป๋า")

    req = WalletRequest(user_id=user.id, type=body.type, amount=amount, desc=desc, status="pending")
    db.add(req)
    db.flush()
    if body.type == "withdraw":
        move_money(db, user.id, -amount, "withdraw", f"{desc} (คำขอ #{req.id})")   # กันยอดไว้ / ยอดไม่พอ → 400
    db.commit()
    w = get_wallet(db, user.id)
    return {"ok": True, "pending": True, "request": request_dict(req), "balance": float(w.balance or 0)}
