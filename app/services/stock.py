"""NRW stock — ทุกการเปลี่ยนสต็อกต้องผ่าน move_stock() เพื่อบันทึกประวัติ (ใครทำ, เท่าไร, เหลือเท่าไร)

  move_stock(db, p, -2, "sale", "ออเดอร์ #12", user_id)      ตัด/เพิ่มสต็อก (ติดลบไม่ได้ → 400)
  set_stock(db, p, 40, "count", "ตรวจนับ", user_id)          ตั้งยอดใหม่ (ตรวจนับ/แก้ในฟอร์ม)
ไม่ commit — ผู้เรียก commit เอง"""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.shop import StockMove, StockSetting

KIND_LABELS = {"in": "📥 รับเข้า", "out": "📤 เบิกออก", "count": "🔢 ตรวจนับ", "sale": "🛒 ขาย",
               "return": "↩️ คืนจากยกเลิก", "create": "🆕 ลงสินค้า", "edit": "✏️ แก้ในฟอร์ม"}
DEFAULT_LOW = 5


def move_stock(db: Session, p: Product, change: int, kind: str, note: str = "", user_id: int | None = None) -> int:
    new = (p.stock or 0) + int(change)
    if new < 0:
        raise HTTPException(status_code=400, detail=f"{p.name} เหลือ {p.stock or 0} ชิ้น — สต็อกติดลบไม่ได้")
    p.stock = new
    if change:
        db.add(StockMove(product_id=p.id, user_id=user_id, kind=kind, change=int(change), balance=new, note=note[:200]))
    return new


def set_stock(db: Session, p: Product, qty: int, kind: str, note: str = "", user_id: int | None = None) -> int:
    return move_stock(db, p, int(qty) - (p.stock or 0), kind, note, user_id)


def low_map(db: Session, ids) -> dict[int, int]:
    ids = list(ids)
    rows = db.query(StockSetting).filter(StockSetting.product_id.in_(ids)).all() if ids else []
    got = {r.product_id: r.low_at for r in rows}
    return {i: got.get(i, DEFAULT_LOW) for i in ids}


def stock_status(stock: int, low_at: int) -> str:
    return "out" if stock <= 0 else "low" if stock <= low_at else "ok"
