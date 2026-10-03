"""NRW Shop Router — ขายออนไลน์: ดูสินค้า, สั่งซื้อ (จ่ายจากกระเป๋าเงิน), ดูออเดอร์ของฉัน

สั่งซื้อ = หักเงิน + ตัดสต็อก + สร้างออเดอร์ + ให้โทเคน ในรายการเดียว (สำเร็จพร้อมกันหรือไม่สำเร็จเลย)
โทเคนที่ได้: 1 โทเคน ต่อทุก TOKEN_PER_BAHT บาท (ค่าเริ่มต้น 100)
"""
import os
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user
from app.models.product import Product
from app.models.shop import Order, OrderItem, ShipmentEvent, ORDER_STATUS_LABELS
from app.services.wallet_ops import move_money, move_tokens

router = APIRouter()
TOKEN_PER_BAHT = int(os.getenv("TOKEN_PER_BAHT", "100"))


def product_dict(p: Product) -> dict:
    return {"id": p.id, "name": p.name, "description": p.description or "", "price": p.price,
            "stock": p.stock or 0, "image_url": p.image_url or "",
            "created_at": p.created_at.isoformat() if p.created_at else None}


def order_dict(db: Session, o: Order) -> dict:
    items = db.query(OrderItem).filter(OrderItem.order_id == o.id).all()
    return {"id": o.id, "total": float(o.total), "status": o.status,
            "status_label": ORDER_STATUS_LABELS.get(o.status, o.status),
            "address": o.address, "tracking": o.tracking,
            "date": o.created_at.strftime("%d/%m/%Y %H:%M") if o.created_at else "—",
            "items": [{"product_id": i.product_id, "name": i.name, "price": float(i.price), "qty": i.qty}
                      for i in items]}


@router.get("/")
async def shop_home():
    return {"module": "Shop", "status": "ok"}


@router.get("/products")
def list_products(db: Session = Depends(get_db)):
    """รายการสินค้าที่เปิดขาย"""
    products = (db.query(Product).filter(Product.is_active == True)
                  .order_by(Product.created_at.desc(), Product.id.desc()).all())
    return {"products": [product_dict(p) for p in products]}


@router.get("/products/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    p = db.query(Product).filter(Product.id == product_id, Product.is_active == True).first()
    if not p:
        raise HTTPException(status_code=404, detail="ไม่พบสินค้า")
    return product_dict(p)


class CartItem(BaseModel):
    product_id: int
    qty: int = Field(..., ge=1, le=999)


class OrderCreate(BaseModel):
    items: list[CartItem] = Field(..., min_length=1, max_length=50)
    address: str = Field(..., min_length=5, max_length=500)


@router.post("/orders")
def create_order(body: OrderCreate, request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    qty_by_id: dict[int, int] = {}
    for it in body.items:
        qty_by_id[it.product_id] = qty_by_id.get(it.product_id, 0) + it.qty

    # ล็อกแถวสินค้า (เรียงตาม id กัน deadlock) แล้วเช็คสต็อก
    products = (db.query(Product).filter(Product.id.in_(qty_by_id.keys()))
                  .order_by(Product.id).with_for_update().all())
    found = {p.id: p for p in products}
    total = Decimal("0")
    for pid, qty in qty_by_id.items():
        p = found.get(pid)
        if not p or not p.is_active:
            raise HTTPException(status_code=404, detail=f"ไม่พบสินค้า #{pid}")
        if (p.stock or 0) < qty:
            raise HTTPException(status_code=400, detail=f"{p.name} เหลือ {p.stock or 0} ชิ้น")
        total += Decimal(str(p.price)) * qty

    order = Order(user_id=user.id, total=total, status="paid", address=body.address.strip())
    db.add(order)
    db.flush()
    move_money(db, user.id, -total, "purchase", f"ซื้อสินค้า ออเดอร์ #{order.id}")   # เงินไม่พอ → 400 + rollback
    for pid, qty in qty_by_id.items():
        p = found[pid]
        p.stock = (p.stock or 0) - qty
        db.add(OrderItem(order_id=order.id, product_id=pid, name=p.name, price=p.price, qty=qty))
    db.add(ShipmentEvent(order_id=order.id, status="paid", note="ชำระเงินแล้ว รอแพ็กสินค้า"))
    tokens = int(total // TOKEN_PER_BAHT) if TOKEN_PER_BAHT > 0 else 0
    if tokens:
        move_tokens(db, user.id, tokens, "earn", f"ได้จากออเดอร์ #{order.id}")
    db.commit()
    return {**order_dict(db, order), "tokens_earned": tokens}


@router.get("/orders")
def my_orders(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    orders = db.query(Order).filter(Order.user_id == user.id).order_by(Order.id.desc()).limit(50).all()
    return {"orders": [order_dict(db, o) for o in orders]}
