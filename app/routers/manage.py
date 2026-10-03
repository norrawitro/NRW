"""NRW Manage Router — แผงผู้ดูแลระบบบนเว็บ (/manage) — ต้อง login ด้วยบัญชีที่เป็น admin

ตั้งผู้ดูแลคนแรก: python make_admin.py <username>
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_admin, optional_user
from app.models.user import User
from app.models.wallet import WalletRequest
from app.models.product import Product
from app.routers.wallet import request_dict
from app.services.wallet_ops import get_wallet, move_money, move_tokens

router = APIRouter()


@router.get("", response_class=HTMLResponse)
def manage_page(request: Request, db: Session = Depends(get_db)):
    user = optional_user(request, db)
    if not user or not user.is_admin:
        return HTMLResponse('<meta charset="utf-8"><p style="font-family:sans-serif;padding:40px">'
                            'เฉพาะผู้ดูแลระบบ — <a href="/members/login">เข้าสู่ระบบ</a></p>', status_code=403)
    with open("app/templates/manage.html", encoding="utf-8") as f:
        return f.read()


# ─── สมาชิก ─────────────────────────────────────────────────────
@router.get("/api/users")
def list_users(request: Request, db: Session = Depends(get_db)):
    current_admin(request, db)
    users = db.query(User).order_by(User.id.desc()).all()
    out = []
    for u in users:
        w = get_wallet(db, u.id)
        out.append({"id": u.id, "username": u.username, "full_name": u.full_name, "email": u.email,
                    "is_admin": u.is_admin, "is_active": u.is_active,
                    "balance": float(w.balance or 0), "token": int(w.token or 0)})
    db.commit()
    return {"users": out}


@router.post("/api/users/{user_id}/toggle/{field}")
def toggle_user(user_id: int, field: str, request: Request, db: Session = Depends(get_db)):
    admin = current_admin(request, db)
    if field not in ("is_active", "is_admin"):
        raise HTTPException(status_code=400, detail="field ไม่ถูกต้อง")
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="ไม่พบสมาชิก")
    if u.id == admin.id:
        raise HTTPException(status_code=400, detail="เปลี่ยนสถานะบัญชีตัวเองไม่ได้")
    setattr(u, field, not getattr(u, field))
    db.commit()
    return {"id": u.id, field: getattr(u, field)}


class Adjust(BaseModel):
    amount: float = 0          # บาท (+/-)
    token: int = 0             # โทเคน (+/-)
    note: str = Field("", max_length=200)


@router.post("/api/users/{user_id}/adjust")
def adjust_user(user_id: int, body: Adjust, request: Request, db: Session = Depends(get_db)):
    admin = current_admin(request, db)
    if not db.query(User.id).filter(User.id == user_id).first():
        raise HTTPException(status_code=404, detail="ไม่พบสมาชิก")
    note = body.note.strip() or f"ปรับยอดโดย {admin.username}"
    if body.amount:
        move_money(db, user_id, body.amount, "admin", note)
    if body.token:
        move_tokens(db, user_id, body.token, "admin", note)
    db.commit()
    w = get_wallet(db, user_id)
    return {"balance": float(w.balance or 0), "token": int(w.token or 0)}


# ─── คำขอเติม/ถอนเงิน ───────────────────────────────────────────
@router.get("/api/wallet-requests")
def wallet_requests(request: Request, status: str = "pending", db: Session = Depends(get_db)):
    current_admin(request, db)
    q = db.query(WalletRequest, User).join(User, User.id == WalletRequest.user_id)
    if status != "all":
        q = q.filter(WalletRequest.status == status)
    rows = q.order_by(WalletRequest.id.desc()).limit(200).all()
    return {"requests": [{**request_dict(r), "username": u.username, "full_name": u.full_name,
                          "decided_by": r.decided_by} for r, u in rows]}


@router.post("/api/wallet-requests/{req_id}/{action}")
def decide_request(req_id: int, action: str, request: Request, db: Session = Depends(get_db)):
    admin = current_admin(request, db)
    if action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="action ต้องเป็น approve หรือ reject")
    r = db.query(WalletRequest).filter(WalletRequest.id == req_id).with_for_update().first()
    if not r:
        raise HTTPException(status_code=404, detail="ไม่พบคำขอ")
    if r.status != "pending":
        raise HTTPException(status_code=400, detail="คำขอนี้ดำเนินการไปแล้ว")
    r.status = "approved" if action == "approve" else "rejected"
    r.decided_by = admin.username
    r.decided_at = datetime.now(timezone.utc)
    if r.type == "topup" and action == "approve":
        move_money(db, r.user_id, r.amount, "topup", f"{r.desc} (คำขอ #{r.id})")
    if r.type == "withdraw" and action == "reject":
        move_money(db, r.user_id, r.amount, "refund", f"คืนเงิน — คำขอถอน #{r.id} ถูกปฏิเสธ")
    db.commit()
    return request_dict(r)


# ─── สินค้า ─────────────────────────────────────────────────────
class ProductIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field("", max_length=5000)
    price: float = Field(..., ge=0)
    stock: int = Field(0, ge=0)
    image_url: str = Field("", max_length=500)
    is_active: bool = True


def product_dict(p: Product) -> dict:
    return {"id": p.id, "name": p.name, "description": p.description or "", "price": p.price,
            "stock": p.stock or 0, "image_url": p.image_url or "", "is_active": p.is_active}


@router.get("/api/products")
def all_products(request: Request, db: Session = Depends(get_db)):
    current_admin(request, db)
    return {"products": [product_dict(p) for p in db.query(Product).order_by(Product.id.desc()).all()]}


@router.post("/api/products")
def create_product(body: ProductIn, request: Request, db: Session = Depends(get_db)):
    current_admin(request, db)
    p = Product(**body.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return product_dict(p)


@router.put("/api/products/{product_id}")
def update_product(product_id: int, body: ProductIn, request: Request, db: Session = Depends(get_db)):
    current_admin(request, db)
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="ไม่พบสินค้า")
    for k, v in body.model_dump().items():
        setattr(p, k, v)
    db.commit()
    return product_dict(p)
