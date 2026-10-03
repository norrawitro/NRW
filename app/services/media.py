"""NRW media — แนบรูปให้เนื้อหาทุกประเภทด้วยวิธีเดียวกัน

วิธีใช้ใน router:
  ตอนสร้าง/แก้ไข:  set_images(db, "listing", l.id, body.images)   (สูงสุด MAX_IMAGES รูป)
  ตอนแสดง:        imgs = images_map(db, "listing", [ids])  →  imgs.get(id, [])
รูปต้องอัปโหลดผ่าน POST /media/images ก่อน (ได้ url /media/images/xxx) หรือเป็นลิงก์ http(s)"""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.media import ItemImage

MAX_IMAGES = 5


def clean_urls(urls) -> list[str]:
    out = []
    for u in (urls or [])[:MAX_IMAGES]:
        u = (u or "").strip()
        if not u:
            continue
        if not (u.startswith(("/media/images/", "/shop/images/")) or u.lower().startswith(("http://", "https://"))):
            raise HTTPException(status_code=400, detail="ลิงก์รูปไม่ถูกต้อง")
        out.append(u[:500])
    return out


def set_images(db: Session, kind: str, item_id: int, urls) -> list[str]:
    urls = clean_urls(urls)
    db.query(ItemImage).filter(ItemImage.kind == kind, ItemImage.item_id == item_id).delete()
    for i, u in enumerate(urls):
        db.add(ItemImage(kind=kind, item_id=item_id, position=i, url=u))
    return urls


def images_map(db: Session, kind: str, ids) -> dict[int, list[str]]:
    ids = list(ids)
    if not ids:
        return {}
    out: dict[int, list[str]] = {}
    for im in (db.query(ItemImage).filter(ItemImage.kind == kind, ItemImage.item_id.in_(ids))
                 .order_by(ItemImage.item_id, ItemImage.position).all()):
        out.setdefault(im.item_id, []).append(im.url)
    return out
