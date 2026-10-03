"""NRW Logistics Router — คลังสินค้า/ขนส่ง

สมาชิก: ดูเส้นทางพัสดุของออเดอร์ตัวเอง
ผู้ดูแล: คิวออเดอร์, เปลี่ยนสถานะ (แพ็ก → ส่ง → ได้รับ), ยกเลิก (คืนเงิน+คืนสต็อก), สต็อกใกล้หมด
"""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user, current_admin
from app.models.user import User
from app.models.product import Product
from app.models.shop import Order, OrderItem, ShipmentEvent, ORDER_STATUSES, ORDER_STATUS_LABELS
from app.routers.shop import order_dict
from app.models.wallet import TokenTransaction
from app.services.wallet_ops import move_money, move_tokens, get_wallet

router = APIRouter()

# เปลี่ยนสถานะได้แค่ตามลำดับนี้
NEXT_STATUS = {"paid": ["packed", "cancelled"], "packed": ["shipped", "cancelled"],
               "shipped": ["delivered"], "delivered": [], "cancelled": []}
LOW_STOCK = 5


def _timeline(db: Session, order_id: int) -> list[dict]:
    events = (db.query(ShipmentEvent).filter(ShipmentEvent.order_id == order_id)
                .order_by(ShipmentEvent.id).all())
    return [{"status": e.status, "label": ORDER_STATUS_LABELS.get(e.status, e.status), "note": e.note,
             "date": e.created_at.strftime("%d/%m/%Y %H:%M") if e.created_at else "—"} for e in events]


@router.get("/orders/{order_id}")
def track_order(order_id: int, request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    o = db.query(Order).filter(Order.id == order_id).first()
    if not o or (o.user_id != user.id and not user.is_admin):
        raise HTTPException(status_code=404, detail="ไม่พบออเดอร์")
    return {**order_dict(db, o), "timeline": _timeline(db, o.id)}


@router.get("/queue")
def queue(request: Request, status: str = "active", db: Session = Depends(get_db)):
    """ออเดอร์ทั้งหมดสำหรับผู้ดูแล — status=active (ยังไม่จบ) / all / ชื่อสถานะ"""
    current_admin(request, db)
    q = db.query(Order, User).join(User, User.id == Order.user_id)
    if status == "active":
        q = q.filter(Order.status.in_(["paid", "packed", "shipped"]))
    elif status != "all":
        q = q.filter(Order.status == status)
    rows = q.order_by(Order.id.desc()).limit(200).all()
    return {"orders": [{**order_dict(db, o), "username": u.username, "full_name": u.full_name,
                        "next": NEXT_STATUS.get(o.status, [])} for o, u in rows]}


class StatusUpdate(BaseModel):
    status: str
    tracking: str = Field("", max_length=100)
    note: str = Field("", max_length=200)


@router.post("/orders/{order_id}/status")
def update_status(order_id: int, body: StatusUpdate, request: Request, db: Session = Depends(get_db)):
    admin = current_admin(request, db)
    o = db.query(Order).filter(Order.id == order_id).with_for_update().first()
    if not o:
        raise HTTPException(status_code=404, detail="ไม่พบออเดอร์")
    if body.status not in ORDER_STATUSES or body.status not in NEXT_STATUS.get(o.status, []):
        raise HTTPException(status_code=400,
                            detail=f"เปลี่ยนจาก {ORDER_STATUS_LABELS.get(o.status)} เป็น {body.status} ไม่ได้")
    if body.status == "cancelled":
        # คืนเงิน + คืนสต็อก
        move_money(db, o.user_id, Decimal(str(o.total)), "refund", f"คืนเงิน ออเดอร์ #{o.id} ถูกยกเลิก")
        # ดึงโทเคนที่ได้จากออเดอร์นี้คืน (เท่าที่ผู้ใช้ยังมีอยู่)
        earned = sum(t.amount for t in db.query(TokenTransaction).filter(
            TokenTransaction.user_id == o.user_id, TokenTransaction.kind == "earn",
            TokenTransaction.note == f"ได้จากออเดอร์ #{o.id}").all())
        take = min(earned, int(get_wallet(db, o.user_id, lock=True).token or 0))
        if take > 0:
            move_tokens(db, o.user_id, -take, "admin", f"คืนโทเคน ออเดอร์ #{o.id} ถูกยกเลิก")
        for it in db.query(OrderItem).filter(OrderItem.order_id == o.id).all():
            p = db.query(Product).filter(Product.id == it.product_id).with_for_update().first()
            if p:
                p.stock = (p.stock or 0) + it.qty
    if body.tracking.strip():
        o.tracking = body.tracking.strip()
    o.status = body.status
    note = body.note.strip() or f"{ORDER_STATUS_LABELS[body.status]} (โดย {admin.username})"
    db.add(ShipmentEvent(order_id=o.id, status=body.status, note=note))
    db.commit()
    return {**order_dict(db, o), "timeline": _timeline(db, o.id)}


@router.get("/inventory")
def inventory(request: Request, db: Session = Depends(get_db)):
    """สต็อกสินค้าทั้งหมด เรียงจากใกล้หมดก่อน"""
    current_admin(request, db)
    products = db.query(Product).order_by(Product.stock.asc(), Product.id).all()
    return {"low_stock_threshold": LOW_STOCK,
            "products": [{"id": p.id, "name": p.name, "stock": p.stock or 0, "is_active": p.is_active,
                          "low": (p.stock or 0) <= LOW_STOCK} for p in products]}


class StockAdjust(BaseModel):
    delta: int = Field(..., ge=-100000, le=100000)


@router.post("/inventory/{product_id}")
def adjust_stock(product_id: int, body: StockAdjust, request: Request, db: Session = Depends(get_db)):
    current_admin(request, db)
    p = db.query(Product).filter(Product.id == product_id).with_for_update().first()
    if not p:
        raise HTTPException(status_code=404, detail="ไม่พบสินค้า")
    if (p.stock or 0) + body.delta < 0:
        raise HTTPException(status_code=400, detail="สต็อกติดลบไม่ได้")
    p.stock = (p.stock or 0) + body.delta
    db.commit()
    return {"id": p.id, "stock": p.stock}
