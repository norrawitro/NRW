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
from app.models.shop import Order, OrderItem, ShipmentEvent, OrderSeller, ORDER_STATUSES, ORDER_STATUS_LABELS
from app.routers.shop import order_dict
from app.models.wallet import TokenTransaction
from app.services.wallet_ops import move_money, move_tokens, get_wallet
from app.services.stock import move_stock

router = APIRouter()

# เปลี่ยนสถานะได้แค่ตามลำดับนี้
NEXT_STATUS = {"paid": ["packed", "cancelled"], "packed": ["shipped", "cancelled"],
               "shipped": ["delivered"], "delivered": [], "cancelled": []}
# ผู้ขายทำได้แค่ แพ็ก/ส่ง/ยกเลิก — "ได้รับแล้ว" ต้องให้ผู้ซื้อ (หรือผู้ดูแล) กด เพื่อปล่อยเงินให้ผู้ขาย
SELLER_NEXT = {"paid": ["packed", "cancelled"], "packed": ["shipped", "cancelled"]}
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


def apply_status(db: Session, o: Order, status: str, actor: str, tracking: str = "", note: str = "") -> None:
    """เปลี่ยนสถานะออเดอร์ (ไม่ commit) — ยกเลิก: คืนเงิน/สต็อก/โทเคน · ได้รับแล้ว: โอนเงินให้ผู้ขาย"""
    if status not in ORDER_STATUSES or status not in NEXT_STATUS.get(o.status, []):
        raise HTTPException(status_code=400,
                            detail=f"เปลี่ยนจาก {ORDER_STATUS_LABELS.get(o.status)} เป็น {status} ไม่ได้")
    seller = db.query(OrderSeller).filter(OrderSeller.order_id == o.id).first()
    if status == "cancelled":
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
                move_stock(db, p, it.qty, "return", f"ออเดอร์ #{o.id} ถูกยกเลิก (โดย {actor})")
    if status == "delivered" and seller and not seller.paid_out:
        move_money(db, seller.seller_id, Decimal(str(o.total)), "sale", f"รายได้จากออเดอร์ #{o.id}")
        seller.paid_out = 1
    if tracking.strip():
        o.tracking = tracking.strip()
    o.status = status
    db.add(ShipmentEvent(order_id=o.id, status=status, note=note.strip() or f"{ORDER_STATUS_LABELS[status]} (โดย {actor})"))


@router.post("/orders/{order_id}/status")
def update_status(order_id: int, body: StatusUpdate, request: Request, db: Session = Depends(get_db)):
    """ผู้ดูแล: ทุกสถานะ · ผู้ขายของออเดอร์: แพ็ก/ส่ง/ยกเลิก"""
    me = current_user(request, db)
    o = db.query(Order).filter(Order.id == order_id).with_for_update().first()
    if not o:
        raise HTTPException(status_code=404, detail="ไม่พบออเดอร์")
    if not me.is_admin:
        seller = db.query(OrderSeller).filter(OrderSeller.order_id == o.id).first()
        if not seller or seller.seller_id != me.id:
            raise HTTPException(status_code=403, detail="เฉพาะผู้ขายของออเดอร์นี้หรือผู้ดูแล")
        if body.status not in SELLER_NEXT.get(o.status, []):
            raise HTTPException(status_code=400, detail="ผู้ขายเปลี่ยนเป็นสถานะนี้ไม่ได้ (ผู้ซื้อต้องกดได้รับสินค้าเอง)")
    apply_status(db, o, body.status, me.username, body.tracking, body.note)
    db.commit()
    return {**order_dict(db, o), "timeline": _timeline(db, o.id)}


@router.post("/orders/{order_id}/received")
def mark_received(order_id: int, request: Request, db: Session = Depends(get_db)):
    """ผู้ซื้อยืนยันได้รับสินค้า → ปล่อยเงินให้ผู้ขาย"""
    me = current_user(request, db)
    o = db.query(Order).filter(Order.id == order_id, Order.user_id == me.id).with_for_update().first()
    if not o:
        raise HTTPException(status_code=404, detail="ไม่พบออเดอร์ของคุณ")
    if o.status != "shipped":
        raise HTTPException(status_code=400, detail="กดได้เมื่อผู้ขายส่งสินค้าแล้ว")
    apply_status(db, o, "delivered", me.username, note="ผู้ซื้อยืนยันได้รับสินค้าแล้ว")
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
    admin = current_admin(request, db)
    p = db.query(Product).filter(Product.id == product_id).with_for_update().first()
    if not p:
        raise HTTPException(status_code=404, detail="ไม่พบสินค้า")
    move_stock(db, p, body.delta, "in" if body.delta > 0 else "out", "ปรับโดยผู้ดูแล", admin.id)
    db.commit()
    return {"id": p.id, "stock": p.stock}
