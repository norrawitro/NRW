"""NRW Moderation Admin Router — คิวอนุมัติเนื้อหาสำหรับผู้ดูแล (แท็บ "อนุมัติเนื้อหา" ใน /manage)

GET  /manage/api/moderation?status=pending|approved|rejected&kind=   รายการพร้อมตัวอย่างเนื้อหา
POST /manage/api/moderation/{id}/approve | /reject  {reason}
ผลข้างเคียง: ปฏิเสธโฆษณา = คืนเงินผู้ซื้อ · อนุมัติหลักฐานออกกำลังกาย = ให้โทเคน"""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_admin
from app.models.moderation import Moderation
from app.models.wallet import WalletRequest
from app.models.post import Post
from app.models.product import Product
from app.models.market import Listing
from app.models.wanted import WantedPost
from app.models.work import Course, Job, Ad
from app.models.community import Video, Event, CreatorPost, HealthLog
from app.services.helpers import fmt, names
from app.services.moderation import LABELS, decide
from app.services.wallet_ops import move_money
from app.services.media import images_map

router = APIRouter()


def _preview(db: Session, kind: str, item_id: int) -> dict:
    """หัวข้อ + รายละเอียด + สื่อ (รูป/วิดีโอ/ลิงก์) ของเนื้อหาแต่ละประเภท"""
    def one(model):
        return db.query(model).filter(model.id == item_id).first()
    x = None
    if kind == "post" and (x := one(Post)):
        return {"title": x.text[:80], "detail": x.text}
    if kind == "product" and (x := one(Product)):
        return {"title": x.name, "detail": f"฿{x.price:,.2f} · สต็อก {x.stock}\n{x.description or ''}", "image": x.image_url}
    if kind == "listing" and (x := one(Listing)):
        return {"title": x.title, "detail": f"{'ให้เช่า' if x.kind == 'rent' else 'ขาย'} ฿{float(x.price):,.2f}\n{x.description}"}
    if kind == "course" and (x := one(Course)):
        return {"title": x.title, "detail": f"ราคา ฿{float(x.price):,.2f}\n{x.description}"}
    if kind == "job" and (x := one(Job)):
        return {"title": x.title, "detail": f"งบ ฿{float(x.budget):,.2f}\n{x.description}"}
    if kind == "ad" and (x := one(Ad)):
        return {"title": x.title, "detail": f"{x.text}\nจ่ายแล้ว ฿{float(x.paid):,.2f} · ถึง {fmt(x.ends_at)}", "link": x.link}
    if kind == "video" and (x := one(Video)):
        return {"title": x.title, "detail": x.description, "video": f"/video/{x.id}/file"}
    if kind == "event" and (x := one(Event)):
        return {"title": x.title, "detail": f"{fmt(x.starts_at)} · {x.place} · ฿{float(x.price):,.2f}\n{x.description}"}
    if kind == "creator_post" and (x := one(CreatorPost)):
        return {"title": x.title, "detail": x.body}
    if kind == "health" and (x := one(HealthLog)):
        return {"title": f"{x.activity} {x.minutes} นาที" + (f" · {x.steps:,} ก้าว" if x.steps else ""),
                "detail": f"วันที่ {x.day:%d/%m/%Y}", "image": f"/health/evidence/{x.id}"}
    if kind == "wanted" and (x := one(WantedPost)):
        return {"title": x.title, "detail": f"งบ ฿{float(x.budget):,.2f}\n{x.description}"}
    return {"title": "(ถูกลบไปแล้ว)", "detail": ""}


def preview(db: Session, kind: str, item_id: int) -> dict:
    """_preview + รูปที่แนบ (ทุกประเภทใช้ตาราง ItemImage ร่วมกัน)"""
    d = _preview(db, kind, item_id)
    imgs = images_map(db, kind, [item_id]).get(item_id, [])
    if imgs:
        d["images"] = imgs
        d.setdefault("image", imgs[0])
    return d


@router.get("/api/pending-count")
def pending_count(request: Request, db: Session = Depends(get_db)):
    """ตัวเลขบนปุ่ม 🛡️ อนุมัติ ที่หัวเว็บ (เฉพาะผู้ดูแล)"""
    current_admin(request, db)
    content = db.query(Moderation).filter(Moderation.status == "pending").count()
    money = db.query(WalletRequest).filter(WalletRequest.status == "pending").count()
    return {"content": content, "money": money, "total": content + money}


@router.get("/api/moderation")
def queue(request: Request, status: str = "pending", kind: str = "", db: Session = Depends(get_db)):
    current_admin(request, db)
    q = db.query(Moderation)
    if status != "all":
        q = q.filter(Moderation.status == status)
    if kind:
        q = q.filter(Moderation.kind == kind)
    rows = q.order_by(Moderation.id.desc() if status != "pending" else Moderation.id).limit(200).all()
    who = names(db, [m.owner_id for m in rows])
    counts = {k: db.query(Moderation).filter(Moderation.kind == k, Moderation.status == "pending").count() for k in LABELS}
    return {"labels": LABELS, "pending_counts": counts,
            "items": [{"id": m.id, "kind": m.kind, "kind_label": LABELS.get(m.kind, m.kind), "status": m.status,
                       "reason": m.reason, "owner": who.get(m.owner_id, "—"), "date": fmt(m.created_at),
                       "decided_by": m.decided_by, **preview(db, m.kind, m.item_id)} for m in rows]}


class Decision(BaseModel):
    reason: str = Field("", max_length=300)


@router.post("/api/moderation/{mod_id}/{action}")
def decide_item(mod_id: int, action: str, body: Decision, request: Request, db: Session = Depends(get_db)):
    admin = current_admin(request, db)
    if action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="action ต้องเป็น approve หรือ reject")
    m = db.query(Moderation).filter(Moderation.id == mod_id).with_for_update().first()
    if not m:
        raise HTTPException(status_code=404, detail="ไม่พบรายการ")
    was = m.status
    if action == "reject" and not body.reason.strip():
        raise HTTPException(status_code=400, detail="กรุณาใส่เหตุผลที่ไม่อนุมัติ (เจ้าของจะเห็น)")
    decide(db, m, action == "approve", admin.username, body.reason)
    # ผลข้างเคียงเฉพาะประเภท
    if m.kind == "ad" and action == "reject" and was != "rejected":
        ad = db.query(Ad).filter(Ad.id == m.item_id).first()
        if ad and Decimal(str(ad.paid)) > 0:
            move_money(db, ad.owner_id, Decimal(str(ad.paid)), "refund", f"คืนเงินโฆษณา '{ad.title}' (ไม่ผ่านการอนุมัติ)")
            ad.paid, ad.is_active = 0, False
    if m.kind == "health" and action == "approve":
        from app.routers.health import award_tokens
        log = db.query(HealthLog).filter(HealthLog.id == m.item_id).first()
        if log:
            award_tokens(db, log)
    db.commit()
    return {"id": m.id, "status": m.status}
