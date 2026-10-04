"""NRW Stock Router — จัดการสต็อกสินค้า (ผู้ขายจัดการของร้านตัวเอง, ผู้ดูแลจัดการได้ทุกชิ้น)

GET  /stock?scope=mine|platform|all          รายการสินค้า + คงเหลือ + สถานะ (หมด/ใกล้หมด/ปกติ) + สรุป
POST /stock/{id}/move   {kind: in|out|count, qty, note}   รับเข้า / เบิกออก / ตรวจนับ (ตั้งยอดใหม่)
PUT  /stock/{id}/settings {low_at}            จุดแจ้งเตือนใกล้หมด
GET  /stock/{id}/history                      ประวัติความเคลื่อนไหว
GET  /stock/moves                             ความเคลื่อนไหวล่าสุดของสินค้าที่ฉันดูแล
GET  /stock/export.csv?scope=                 ส่งออกเป็นไฟล์ CSV (เปิดใน Excel ได้)"""
import csv
import io
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user
from app.models.user import User
from app.models.product import Product
from app.models.shop import ProductSeller, StockMove, StockSetting
from app.services.helpers import fmt, names, now
from app.services.stock import KIND_LABELS, move_stock, set_stock, low_map, stock_status

router = APIRouter()
STATUS_LABELS = {"out": "หมด", "low": "ใกล้หมด", "ok": "ปกติ"}


def _products(db: Session, me: User, scope: str) -> list[Product]:
    sellers = db.query(ProductSeller)
    if scope == "mine":
        ids = [r.product_id for r in sellers.filter(ProductSeller.seller_id == me.id).all()]
        return db.query(Product).filter(Product.id.in_(ids)).all() if ids else []
    if not me.is_admin:
        raise HTTPException(status_code=403, detail="เฉพาะผู้ดูแล")
    if scope == "platform":
        owned = {r.product_id for r in sellers.all()}
        return [p for p in db.query(Product).all() if p.id not in owned]
    return db.query(Product).all()


def _can_manage(db: Session, me: User, product_id: int) -> Product:
    p = db.query(Product).filter(Product.id == product_id).with_for_update().first()
    if not p:
        raise HTTPException(status_code=404, detail="ไม่พบสินค้า")
    owner = db.query(ProductSeller).filter(ProductSeller.product_id == p.id).first()
    if not me.is_admin and (not owner or owner.seller_id != me.id):
        raise HTTPException(status_code=403, detail="จัดการได้เฉพาะสินค้าของร้านคุณ")
    return p


def _rows(db: Session, products: list[Product]) -> list[dict]:
    ids = [p.id for p in products]
    lows = low_map(db, ids)
    since = now() - timedelta(days=30)
    sold = dict(db.query(StockMove.product_id, func.sum(StockMove.change)).filter(
        StockMove.product_id.in_(ids), StockMove.kind.in_(["sale", "return"]), StockMove.created_at >= since)
        .group_by(StockMove.product_id).all()) if ids else {}
    out = []
    for p in products:
        stock, low_at = p.stock or 0, lows[p.id]
        st = stock_status(stock, low_at)
        sold30 = -int(sold.get(p.id) or 0)
        out.append({"id": p.id, "name": p.name, "image_url": p.image_url or "", "price": float(p.price or 0),
                    "stock": stock, "low_at": low_at, "status": st, "status_label": STATUS_LABELS[st],
                    "value": round(stock * float(p.price or 0), 2), "sold_30d": max(sold30, 0),
                    "days_left": round(stock / (sold30 / 30), 1) if sold30 > 0 else None, "is_active": bool(p.is_active)})
    order = {"out": 0, "low": 1, "ok": 2}
    return sorted(out, key=lambda r: (order[r["status"]], r["stock"], r["name"]))


@router.get("")
def stock_list(request: Request, scope: str = "mine", db: Session = Depends(get_db)):
    me = current_user(request, db)
    rows = _rows(db, _products(db, me, scope))
    return {"scope": scope, "is_admin": bool(me.is_admin), "products": rows,
            "summary": {"skus": len(rows), "units": sum(r["stock"] for r in rows),
                        "value": round(sum(r["value"] for r in rows), 2),
                        "low": sum(r["status"] == "low" for r in rows), "out": sum(r["status"] == "out" for r in rows)}}


class MoveIn(BaseModel):
    kind: str = Field(..., pattern="^(in|out|count)$")
    qty: int = Field(..., ge=0, le=1_000_000)
    note: str = Field("", max_length=200)


@router.post("/{product_id}/move")
def stock_move(product_id: int, body: MoveIn, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    p = _can_manage(db, me, product_id)
    if body.kind != "count" and body.qty == 0:
        raise HTTPException(status_code=400, detail="จำนวนต้องมากกว่า 0")
    note = body.note.strip()
    if body.kind == "in":
        move_stock(db, p, body.qty, "in", note or "รับสินค้าเข้า", me.id)
    elif body.kind == "out":
        move_stock(db, p, -body.qty, "out", note or "เบิกออก", me.id)
    else:
        set_stock(db, p, body.qty, "count", note or "ตรวจนับสต็อก", me.id)
    db.commit()
    return _rows(db, [p])[0]


class SettingsIn(BaseModel):
    low_at: int = Field(..., ge=0, le=100000)


@router.put("/{product_id}/settings")
def stock_settings(product_id: int, body: SettingsIn, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    p = _can_manage(db, me, product_id)
    s = db.query(StockSetting).filter(StockSetting.product_id == p.id).first()
    if not s:
        s = StockSetting(product_id=p.id)
        db.add(s)
    s.low_at = body.low_at
    db.commit()
    return _rows(db, [p])[0]


def _move_dicts(db: Session, rows: list[StockMove]) -> list[dict]:
    who = names(db, [m.user_id for m in rows])
    pn = {p.id: p.name for p in db.query(Product).filter(Product.id.in_({m.product_id for m in rows})).all()} if rows else {}
    return [{"id": m.id, "product_id": m.product_id, "product": pn.get(m.product_id, "—"), "kind": m.kind,
             "label": KIND_LABELS.get(m.kind, m.kind), "change": m.change, "balance": m.balance, "note": m.note,
             "by": who.get(m.user_id, "ระบบ"), "date": fmt(m.created_at)} for m in rows]


@router.get("/{product_id}/history")
def stock_history(product_id: int, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    p = _can_manage(db, me, product_id)
    rows = db.query(StockMove).filter(StockMove.product_id == p.id).order_by(StockMove.id.desc()).limit(200).all()
    db.rollback()   # ปล่อย lock จาก _can_manage
    return {"product": p.name, "moves": _move_dicts(db, rows)}


@router.get("/moves")
def recent_moves(request: Request, scope: str = "mine", db: Session = Depends(get_db)):
    me = current_user(request, db)
    ids = [p.id for p in _products(db, me, scope)]
    rows = (db.query(StockMove).filter(StockMove.product_id.in_(ids)).order_by(StockMove.id.desc()).limit(50).all()) if ids else []
    return {"moves": _move_dicts(db, rows)}


@router.get("/export.csv")
def export_csv(request: Request, scope: str = "mine", db: Session = Depends(get_db)):
    me = current_user(request, db)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["รหัส", "สินค้า", "ราคา", "คงเหลือ", "แจ้งเตือนเมื่อเหลือ", "สถานะ", "มูลค่า", "ขาย 30 วัน", "พอขายอีก (วัน)", "เปิดขาย"])
    for r in _rows(db, _products(db, me, scope)):
        w.writerow([r["id"], r["name"], r["price"], r["stock"], r["low_at"], r["status_label"], r["value"],
                    r["sold_30d"], r["days_left"] if r["days_left"] is not None else "", "ใช่" if r["is_active"] else "ไม่"])
    return Response("﻿" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=stock.csv"})
