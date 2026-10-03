"""NRW Shop Router — ขายออนไลน์ (แบบตลาด: สมาชิกทุกคนลงขายได้)

ผู้ซื้อ:  ดูสินค้า → ตะกร้า → สั่งซื้อ (จ่ายจากกระเป๋าเงิน) — ตะกร้าหลายร้านแยกเป็นออเดอร์ละร้าน
ผู้ขาย:  ลงสินค้า (อัปโหลดรูปได้), แก้/ปิดขาย, ดูออเดอร์ที่ต้องส่ง (จัดการสถานะที่ /logistics)
เงิน:    พักไว้กับระบบ → ผู้ซื้อกด "ได้รับสินค้าแล้ว" → โอนให้ผู้ขาย (ดู logistics.py)
โทเคน:   ผู้ซื้อได้ 1 โทเคน ต่อทุก TOKEN_PER_BAHT บาท (ค่าเริ่มต้น 100)
"""
import os
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user
from app.models.product import Product
from app.models.shop import Order, OrderItem, ShipmentEvent, ProductSeller, OrderSeller, ORDER_STATUS_LABELS
from app.routers.cloud import UPLOAD_ROOT
from app.services.helpers import names
from app.services.wallet_ops import move_money, move_tokens, to_money
from app.services.moderation import submit, hidden_ids, badge, ensure_visible
from app.services.media import set_images, images_map

router = APIRouter()
TOKEN_PER_BAHT = int(os.getenv("TOKEN_PER_BAHT", "100"))
IMAGE_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif"}
IMAGE_MAX = 5 * 1024 * 1024


def _sellers(db: Session, product_ids) -> dict[int, int]:
    ids = list(product_ids)
    if not ids:
        return {}
    return {r.product_id: r.seller_id for r in db.query(ProductSeller).filter(ProductSeller.product_id.in_(ids)).all()}


def product_dict(p: Product, seller_name: str = "WKW") -> dict:
    return {"id": p.id, "name": p.name, "description": p.description or "", "price": p.price,
            "stock": p.stock or 0, "image_url": p.image_url or "", "is_active": p.is_active, "seller": seller_name,
            "created_at": p.created_at.isoformat() if p.created_at else None}


def order_dict(db: Session, o: Order) -> dict:
    items = db.query(OrderItem).filter(OrderItem.order_id == o.id).all()
    os_ = db.query(OrderSeller).filter(OrderSeller.order_id == o.id).first()
    return {"id": o.id, "total": float(o.total), "status": o.status,
            "status_label": ORDER_STATUS_LABELS.get(o.status, o.status),
            "address": o.address, "tracking": o.tracking,
            "date": o.created_at.strftime("%d/%m/%Y %H:%M") if o.created_at else "—",
            "seller_id": os_.seller_id if os_ else None,
            "seller": names(db, [os_.seller_id]).get(os_.seller_id) if os_ else "WKW",
            "items": [{"product_id": i.product_id, "name": i.name, "price": float(i.price), "qty": i.qty}
                      for i in items]}


@router.get("/")
async def shop_home():
    return {"module": "Shop", "status": "ok"}


@router.get("/products")
def list_products(db: Session = Depends(get_db)):
    """สินค้าที่เปิดขายทั้งหมด (ทุกร้าน)"""
    hidden = hidden_ids(db, "product")
    products = [p for p in db.query(Product).filter(Product.is_active == True)
                  .order_by(Product.created_at.desc(), Product.id.desc()).all() if p.id not in hidden]
    sellers = _sellers(db, [p.id for p in products])
    who = names(db, sellers.values())
    imgs = images_map(db, "product", [p.id for p in products])
    return {"products": [{**product_dict(p, who.get(sellers.get(p.id), "WKW")),
                          "images": imgs.get(p.id) or ([p.image_url] if p.image_url else [])} for p in products]}


@router.get("/products/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    p = db.query(Product).filter(Product.id == product_id, Product.is_active == True).first()
    if not p or p.id in hidden_ids(db, "product"):
        raise HTTPException(status_code=404, detail="ไม่พบสินค้า")
    sid = _sellers(db, [p.id]).get(p.id)
    return product_dict(p, names(db, [sid]).get(sid, "WKW"))


class CartItem(BaseModel):
    product_id: int
    qty: int = Field(..., ge=1, le=999)


class OrderCreate(BaseModel):
    items: list[CartItem] = Field(..., min_length=1, max_length=50)
    address: str = Field(..., min_length=5, max_length=500)


@router.post("/orders")
def create_order(body: OrderCreate, request: Request, db: Session = Depends(get_db)):
    """สั่งซื้อ — แยกเป็น 1 ออเดอร์ต่อ 1 ร้าน, หักเงิน+ตัดสต็อก+ให้โทเคนในรายการเดียว"""
    user = current_user(request, db)
    qty_by_id: dict[int, int] = {}
    for it in body.items:
        qty_by_id[it.product_id] = qty_by_id.get(it.product_id, 0) + it.qty

    products = (db.query(Product).filter(Product.id.in_(qty_by_id.keys()))
                  .order_by(Product.id).with_for_update().all())
    found = {p.id: p for p in products}
    sellers = _sellers(db, qty_by_id.keys())
    groups: dict[int | None, list[int]] = {}
    hidden = hidden_ids(db, "product")
    for pid, qty in qty_by_id.items():
        p = found.get(pid)
        if not p or not p.is_active or pid in hidden:
            raise HTTPException(status_code=404, detail=f"ไม่พบสินค้า #{pid}")
        if (p.stock or 0) < qty:
            raise HTTPException(status_code=400, detail=f"{p.name} เหลือ {p.stock or 0} ชิ้น")
        if sellers.get(pid) == user.id:
            raise HTTPException(status_code=400, detail=f"ซื้อสินค้าของร้านตัวเองไม่ได้ ({p.name})")
        groups.setdefault(sellers.get(pid), []).append(pid)

    created, tokens_total = [], 0
    for seller_id, pids in groups.items():
        total = sum(Decimal(str(found[pid].price)) * qty_by_id[pid] for pid in pids)
        order = Order(user_id=user.id, total=total, status="paid", address=body.address.strip())
        db.add(order)
        db.flush()
        move_money(db, user.id, -total, "purchase", f"ซื้อสินค้า ออเดอร์ #{order.id}")   # เงินไม่พอ → 400 + rollback ทั้งหมด
        for pid in pids:
            p = found[pid]
            p.stock = (p.stock or 0) - qty_by_id[pid]
            db.add(OrderItem(order_id=order.id, product_id=pid, name=p.name, price=p.price, qty=qty_by_id[pid]))
        if seller_id:
            db.add(OrderSeller(order_id=order.id, seller_id=seller_id, paid_out=0))
        db.add(ShipmentEvent(order_id=order.id, status="paid", note="ชำระเงินแล้ว รอผู้ขายแพ็กสินค้า"))
        tokens = int(total // TOKEN_PER_BAHT) if TOKEN_PER_BAHT > 0 else 0
        if tokens:
            move_tokens(db, user.id, tokens, "earn", f"ได้จากออเดอร์ #{order.id}")
        tokens_total += tokens
        created.append(order)
    db.commit()
    first = order_dict(db, created[0])
    return {**first, "orders": [o.id for o in created], "tokens_earned": tokens_total}


@router.get("/orders")
def my_orders(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    orders = db.query(Order).filter(Order.user_id == user.id).order_by(Order.id.desc()).limit(50).all()
    return {"orders": [order_dict(db, o) for o in orders]}


# ─── ร้านของฉัน (ผู้ขาย) ─────────────────────────────────────────
class ProductIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field("", max_length=5000)
    price: float = Field(..., gt=0, le=10_000_000)
    stock: int = Field(..., ge=0, le=1_000_000)
    image_url: str = Field("", max_length=500)
    is_active: bool = True
    images: list[str] = Field(default_factory=list, max_length=5)



def _clean_image(url: str) -> str:
    url = (url or "").strip()
    if url and not (url.startswith(("/shop/images/", "/media/images/")) or url.lower().startswith(("http://", "https://"))):
        raise HTTPException(status_code=400, detail="ลิงก์รูปไม่ถูกต้อง")
    return url


def _my_product(db: Session, product_id: int, user_id: int) -> Product:
    if _sellers(db, [product_id]).get(product_id) != user_id:
        raise HTTPException(status_code=404, detail="ไม่พบสินค้าของร้านคุณ")
    return db.query(Product).filter(Product.id == product_id).first()


@router.get("/my/products")
def my_products(request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    ids = [r.product_id for r in db.query(ProductSeller).filter(ProductSeller.seller_id == me.id).all()]
    products = db.query(Product).filter(Product.id.in_(ids)).order_by(Product.id.desc()).all() if ids else []
    imgs = images_map(db, "product", [p.id for p in products])
    return {"products": [{**product_dict(p, me.full_name or me.username), "mod": badge(db, "product", p.id),
                          "images": imgs.get(p.id) or ([p.image_url] if p.image_url else [])} for p in products]}


@router.post("/my/products")
def add_product(body: ProductIn, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    data = body.model_dump(exclude={"images"})
    data["price"] = float(to_money(body.price))
    data["image_url"] = _clean_image(body.images[0] if body.images else body.image_url)
    p = Product(**data)
    db.add(p)
    db.flush()
    db.add(ProductSeller(product_id=p.id, seller_id=me.id))
    set_images(db, "product", p.id, body.images)
    status = submit(db, "product", p.id, me)
    db.commit()
    return {**product_dict(p, me.full_name or me.username), "mod_status": status}


@router.put("/my/products/{product_id}")
def edit_product(product_id: int, body: ProductIn, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    p = _my_product(db, product_id, me.id)
    data = body.model_dump(exclude={"images"})
    data["price"] = float(to_money(body.price))
    data["image_url"] = _clean_image(body.images[0] if body.images else body.image_url)
    for k, v in data.items():
        setattr(p, k, v)
    set_images(db, "product", p.id, body.images)
    status = submit(db, "product", p.id, me)      # แก้แล้วต้องตรวจใหม่ (กันเปลี่ยนเป็นของต้องห้ามหลังอนุมัติ)
    db.commit()
    return {**product_dict(p, me.full_name or me.username), "mod_status": status}


@router.get("/my/sales")
def my_sales(request: Request, db: Session = Depends(get_db)):
    """ออเดอร์ที่ลูกค้าสั่งจากร้านฉัน"""
    me = current_user(request, db)
    ids = [r.order_id for r in db.query(OrderSeller).filter(OrderSeller.seller_id == me.id).all()]
    orders = db.query(Order).filter(Order.id.in_(ids)).order_by(Order.id.desc()).limit(100).all() if ids else []
    buyers = names(db, [o.user_id for o in orders])
    paid = {r.order_id: r.paid_out for r in db.query(OrderSeller).filter(OrderSeller.order_id.in_(ids)).all()} if ids else {}
    from app.routers.logistics import SELLER_NEXT
    return {"orders": [{**order_dict(db, o), "buyer": buyers.get(o.user_id, "—"), "paid_out": bool(paid.get(o.id)),
                        "next": SELLER_NEXT.get(o.status, [])} for o in orders]}


@router.post("/images")
async def upload_image(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """อัปโหลดรูปสินค้า (jpg/png/webp/gif ไม่เกิน 5MB) → คืน url"""
    current_user(request, db)
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="รองรับเฉพาะรูป jpg, png, webp, gif")
    data = await file.read(IMAGE_MAX + 1)
    if len(data) > IMAGE_MAX:
        raise HTTPException(status_code=413, detail="รูปใหญ่เกิน 5MB")
    folder = os.path.join(UPLOAD_ROOT, "products")
    os.makedirs(folder, exist_ok=True)
    name = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(folder, name), "wb") as out:
        out.write(data)
    return {"url": f"/shop/images/{name}"}


@router.get("/images/{name}")
def get_image(name: str):
    base, ext = os.path.splitext(name)
    if ext.lower() not in IMAGE_TYPES or not base.isalnum():
        raise HTTPException(status_code=404, detail="ไม่พบรูป")
    path = os.path.join(UPLOAD_ROOT, "products", name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="ไม่พบรูป")
    return FileResponse(path, media_type=IMAGE_TYPES[ext.lower()])
