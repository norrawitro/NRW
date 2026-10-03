"""NRW wallet operations — เพิ่ม/หักเงินและโทเคนอย่างปลอดภัย (ใช้ร่วมกันทุกระบบที่มีการจ่ายเงิน)

ทุกฟังก์ชันไม่ commit เอง — ผู้เรียกต้อง db.commit() หลังทำทุกอย่างในรายการเสร็จ
เพื่อให้ "หักเงิน + สร้างออเดอร์ + ตัดสต็อก" สำเร็จพร้อมกันหรือไม่สำเร็จเลย
"""
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.wallet import Wallet, WalletTransaction, TokenTransaction

CENT = Decimal("0.01")


def to_money(value) -> Decimal:
    try:
        d = Decimal(str(value)).quantize(CENT)
    except (InvalidOperation, ValueError):
        raise HTTPException(status_code=400, detail="จำนวนเงินไม่ถูกต้อง")
    if not d.is_finite():
        raise HTTPException(status_code=400, detail="จำนวนเงินไม่ถูกต้อง")
    return d


def get_wallet(db: Session, user_id: int, lock: bool = False) -> Wallet:
    """คืนกระเป๋าเงินของผู้ใช้ (สร้างให้ถ้ายังไม่มี) — lock=True ล็อกแถวกันยอดเพี้ยน"""
    q = db.query(Wallet).filter(Wallet.user_id == user_id)
    if lock:
        q = q.with_for_update()
    w = q.first()
    if not w:
        w = Wallet(user_id=user_id, balance=0, token=0)
        db.add(w)
        db.flush()
    return w


def move_money(db: Session, user_id: int, amount, type_: str, desc: str) -> Wallet:
    """amount > 0 = เงินเข้า, < 0 = เงินออก (ยอดติดลบไม่ได้ → 400)"""
    amount = to_money(amount)
    w = get_wallet(db, user_id, lock=True)
    new_balance = Decimal(str(w.balance or 0)) + amount
    if new_balance < 0:
        raise HTTPException(status_code=400, detail=f"ยอดเงินไม่พอ (คงเหลือ ฿{Decimal(str(w.balance or 0)):,.2f})")
    w.balance = new_balance
    db.add(WalletTransaction(user_id=user_id, type=type_, amount=amount, desc=desc[:200]))
    return w


def move_tokens(db: Session, user_id: int, amount: int, kind: str, note: str) -> Wallet:
    """amount > 0 = ได้โทเคน, < 0 = ใช้โทเคน (ติดลบไม่ได้ → 400)"""
    amount = int(amount)
    w = get_wallet(db, user_id, lock=True)
    new_tokens = int(w.token or 0) + amount
    if new_tokens < 0:
        raise HTTPException(status_code=400, detail=f"โทเคนไม่พอ (มี {int(w.token or 0):,})")
    w.token = new_tokens
    db.add(TokenTransaction(user_id=user_id, amount=amount, kind=kind, note=note[:200]))
    return w
