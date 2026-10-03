"""NRW Media Router — อัปโหลด/ดูรูปภาพ (ใช้ร่วมกันทุกระบบ)

POST /media/images  (login)  → {"url": "/media/images/<ชื่อ>"}  jpg/png/webp/gif ไม่เกิน 5MB
GET  /media/images/<ชื่อ>"""
import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user
from app.routers.cloud import UPLOAD_ROOT

router = APIRouter()
TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif"}
MAX_BYTES = 5 * 1024 * 1024


@router.post("/images")
async def upload(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    current_user(request, db)
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in TYPES:
        raise HTTPException(status_code=400, detail="รองรับเฉพาะรูป jpg, png, webp, gif")
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="รูปใหญ่เกิน 5MB")
    folder = os.path.join(UPLOAD_ROOT, "media")
    os.makedirs(folder, exist_ok=True)
    name = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(folder, name), "wb") as out:
        out.write(data)
    return {"url": f"/media/images/{name}"}


@router.get("/images/{name}")
def get_image(name: str):
    base, ext = os.path.splitext(name)
    if ext.lower() not in TYPES or not base.isalnum():
        raise HTTPException(status_code=404, detail="ไม่พบรูป")
    path = os.path.join(UPLOAD_ROOT, "media", name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="ไม่พบรูป")
    return FileResponse(path, media_type=TYPES[ext.lower()], headers={"Cache-Control": "public, max-age=86400"})
