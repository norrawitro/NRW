"""NRW Video Router — วิดีโอความรู้: อัปโหลด (mp4/webm/ogg/mov, ไม่เกิน VIDEO_MAX_MB), ดู, นับยอดวิว
ไฟล์เก็บที่ uploads/videos/ · คอร์สเรียนแนบวิดีโอได้ด้วย video id"""
import os
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user, optional_user
from app.models.community import Video
from app.routers.cloud import UPLOAD_ROOT
from app.services.helpers import fmt, names, get_or_404
from app.services.moderation import submit, hidden_ids, badge, ensure_visible

router = APIRouter()
MAX_BYTES = int(float(os.getenv("VIDEO_MAX_MB", "300")) * 1024 * 1024)
TYPES = {".mp4": "video/mp4", ".webm": "video/webm", ".ogg": "video/ogg", ".mov": "video/quicktime"}


def video_dict(v, who, me, db=None):
    return {"mod": badge(db, "video", v.id) if (db and me and me.id == v.owner_id) else None, "id": v.id, "title": v.title, "description": v.description, "owner": who.get(v.owner_id, "—"),
            "views": v.views, "size": v.size, "date": fmt(v.created_at, False), "is_mine": bool(me and me.id == v.owner_id)}


@router.get("")
def list_videos(request: Request, db: Session = Depends(get_db)):
    me = optional_user(request, db)
    hidden = hidden_ids(db, "video")
    vids = [v for v in db.query(Video).order_by(Video.id.desc()).limit(100).all() if v.id not in hidden or (me and me.id == v.owner_id)]
    who = names(db, [v.owner_id for v in vids])
    return {"videos": [video_dict(v, who, me, db) for v in vids], "max_mb": MAX_BYTES // (1024 * 1024)}


@router.post("")
async def upload(request: Request, file: UploadFile = File(...), title: str = Form(...),
                 description: str = Form(""), db: Session = Depends(get_db)):
    me = current_user(request, db)
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in TYPES:
        raise HTTPException(status_code=400, detail="รองรับเฉพาะ mp4, webm, ogg, mov")
    if not title.strip():
        raise HTTPException(status_code=400, detail="กรุณาใส่ชื่อวิดีโอ")
    folder = os.path.join(UPLOAD_ROOT, "videos")
    os.makedirs(folder, exist_ok=True)
    rel = os.path.join("videos", f"{uuid.uuid4().hex}{ext}")
    dest, size = os.path.join(UPLOAD_ROOT, rel), 0
    try:
        with open(dest, "wb") as out:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise HTTPException(status_code=413, detail=f"ไฟล์ใหญ่เกิน {MAX_BYTES // (1024 * 1024)} MB")
                out.write(chunk)
    except BaseException:
        if os.path.exists(dest):
            os.remove(dest)
        raise
    v = Video(owner_id=me.id, title=title.strip()[:200], description=description.strip()[:5000], path=rel, size=size)
    db.add(v)
    db.flush()
    status = submit(db, "video", v.id, me)
    db.commit()
    return {"id": v.id, "mod_status": status}


@router.get("/{video_id}/file")
def stream(video_id: int, request: Request, db: Session = Depends(get_db)):
    v = get_or_404(db, Video, video_id, "ไม่พบวิดีโอ")
    ensure_visible(db, "video", v.id, v.owner_id, optional_user(request, db), "ไม่พบวิดีโอ")
    full = os.path.join(UPLOAD_ROOT, v.path)
    if not os.path.isfile(full):
        raise HTTPException(status_code=410, detail="ไฟล์วิดีโอหายไป")
    return FileResponse(full, media_type=TYPES.get(os.path.splitext(full)[1], "video/mp4"))


@router.post("/{video_id}/view")
def add_view(video_id: int, db: Session = Depends(get_db)):
    v = get_or_404(db, Video, video_id, "ไม่พบวิดีโอ")
    v.views += 1
    db.commit()
    return {"views": v.views}


@router.delete("/{video_id}")
def delete(video_id: int, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    v = get_or_404(db, Video, video_id, "ไม่พบวิดีโอ")
    if v.owner_id != me.id and not me.is_admin:
        raise HTTPException(status_code=403, detail="ลบได้เฉพาะเจ้าของ")
    full = os.path.join(UPLOAD_ROOT, v.path)
    db.delete(v)
    db.commit()
    if os.path.isfile(full):
        os.remove(full)
    return {"ok": True}
