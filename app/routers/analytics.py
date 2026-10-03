"""NRW Analytics Router — แดชบอร์ดวิเคราะห์

/analytics/me    — สรุปของฉัน (ใช้จ่าย, ออเดอร์, โทเคน, ไฟล์, โพสต์)
/analytics/admin — ภาพรวมทั้งระบบ (เฉพาะผู้ดูแล)
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user, current_admin
from app.models.user import User
from app.models.post import Post
from app.models.cloud import CloudFile
from app.models.wallet import Wallet, WalletRequest
from app.models.shop import Order, OrderItem, ORDER_STATUS_LABELS
from app.models.market import Listing, Deal
from app.models.moderation import Moderation
from app.services.wallet_ops import get_wallet

router = APIRouter()


def _num(v) -> float:
    return float(v or 0)


def _daily_sales(db: Session, days: int = 14, user_id: int | None = None) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days - 1)
    q = db.query(Order).filter(Order.status != "cancelled", Order.created_at >= since.replace(hour=0, minute=0, second=0, microsecond=0))
    if user_id:
        q = q.filter(Order.user_id == user_id)
    totals: dict[str, float] = {}
    for o in q.all():
        key = o.created_at.strftime("%d/%m")
        totals[key] = totals.get(key, 0) + _num(o.total)
    out = []
    for i in range(days):
        key = (since + timedelta(days=i)).strftime("%d/%m")
        out.append({"day": key, "total": round(totals.get(key, 0), 2)})
    return out


@router.get("/me")
def my_stats(request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    w = get_wallet(db, me.id)
    db.commit()
    orders = db.query(Order).filter(Order.user_id == me.id).all()
    spent = sum(_num(o.total) for o in orders if o.status != "cancelled")
    return {
        "balance": _num(w.balance), "token": int(w.token or 0),
        "orders": len(orders), "spent": round(spent, 2),
        "market_bought": db.query(Deal).filter(Deal.buyer_id == me.id).count(),
        "market_listings": db.query(Listing).filter(Listing.seller_id == me.id).count(),
        "files": db.query(CloudFile).filter(CloudFile.user_id == me.id).count(),
        "posts": db.query(Post).filter(Post.author_id == me.id, Post.is_deleted == False).count(),
        "daily_spent": _daily_sales(db, 14, me.id),
    }


@router.get("/admin")
def admin_stats(request: Request, db: Session = Depends(get_db)):
    current_admin(request, db)
    orders = db.query(Order).all()
    by_status = {k: 0 for k in ORDER_STATUS_LABELS}
    for o in orders:
        by_status[o.status] = by_status.get(o.status, 0) + 1
    sales = sum(_num(o.total) for o in orders if o.status != "cancelled")
    top = (db.query(OrderItem.name, func.sum(OrderItem.qty).label("qty"))
             .join(Order, Order.id == OrderItem.order_id).filter(Order.status != "cancelled")
             .group_by(OrderItem.name).order_by(func.sum(OrderItem.qty).desc()).limit(5).all())
    return {
        "users": db.query(User).count(),
        "active_users": db.query(User).filter(User.is_active == True).count(),
        "money_in_wallets": round(_num(db.query(func.sum(Wallet.balance)).scalar()), 2),
        "pending_wallet_requests": db.query(WalletRequest).filter(WalletRequest.status == "pending").count(),
        "pending_content": db.query(Moderation).filter(Moderation.status == "pending").count(),
        "orders": len(orders), "sales": round(sales, 2),
        "orders_by_status": [{"status": k, "label": ORDER_STATUS_LABELS.get(k, k), "count": v} for k, v in by_status.items()],
        "top_products": [{"name": n, "qty": int(q or 0)} for n, q in top],
        "market_active": db.query(Listing).filter(Listing.status == "active").count(),
        "market_deals": db.query(Deal).count(),
        "daily_sales": _daily_sales(db, 14),
    }
