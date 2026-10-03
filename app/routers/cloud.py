"""NRW Cloud Router — folders + real file upload/download, per-user"""
import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.auth import get_current_user_from_cookie
from app.models.user import User
from app.models.cloud import CloudFolder, CloudFile

router = APIRouter()

UPLOAD_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
STORAGE_TOTAL_GB = 50  # quota ต่อ user (GB)


class FolderCreate(BaseModel):
    name: str
    parent_id: int | None = None  # None = root


def _require_user(request: Request, db: Session) -> User:
    payload = get_current_user_from_cookie(request)
    if not payload:
        raise HTTPException(status_code=401, detail="กรุณา login ก่อน")
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=401, detail="ไม่พบผู้ใช้")
    return user


def _user_dir(user_id: int) -> str:
    d = os.path.join(UPLOAD_ROOT, str(user_id))
    os.makedirs(d, exist_ok=True)
    return d


def _storage_used(db: Session, user_id: int) -> float:
    total_bytes = sum(f.size or 0 for f in
                      db.query(CloudFile).filter(CloudFile.user_id == user_id).all())
    return round(total_bytes / (1024 ** 3), 3)


def _folder_dict(f: CloudFolder, db: Session) -> dict:
    count = db.query(CloudFile).filter(CloudFile.folder_id == f.id).count()
    return {"id": f.id, "name": f.name, "type": "folder", "count": count, "icon": "📁"}


def _file_dict(f: CloudFile) -> dict:
    ext = os.path.splitext(f.name)[1].lower()
    icon = {"pdf": "📄", "doc": "📝", "docx": "📝", "xls": "📊", "xlsx": "📊",
            "png": "🖼️", "jpg": "🖼️", "jpeg": "🖼️", "gif": "🖼️", "mp4": "🎬"}.get(ext.lstrip("."), "📄")
    return {"id": f.id, "name": f.name, "type": "file", "size": f.size, "icon": icon}


# ─── GET /cloud — storage + items ในโฟลเดอร์ปัจจุบัน ──────────────
@router.get("")
def list_cloud(request: Request, folder_id: int | None = None, db: Session = Depends(get_db)):
    user = _require_user(request, db)
    items = []
    if folder_id is None:
        # root: โฟลเดอร์ parent_id NULL + ไฟล์ folder_id NULL
        items += [_folder_dict(f, db) for f in
                  db.query(CloudFolder).filter(CloudFolder.user_id == user.id,
                                                CloudFolder.parent_id.is_(None)).all()]
        items += [_file_dict(f) for f in
                  db.query(CloudFile).filter(CloudFile.user_id == user.id,
                                              CloudFile.folder_id.is_(None)).all()]
    else:
        folder = db.query(CloudFolder).filter(
            CloudFolder.id == folder_id, CloudFolder.user_id == user.id).first()
        if not folder:
            raise HTTPException(status_code=404, detail="ไม่พบโฟลเดอร์")
        items += [_folder_dict(f, db) for f in
                  db.query(CloudFolder).filter(CloudFolder.user_id == user.id,
                                                CloudFolder.parent_id == folder_id).all()]
        items += [_file_dict(f) for f in
                  db.query(CloudFile).filter(CloudFile.user_id == user.id,
                                              CloudFile.folder_id == folder_id).all()]
    return {
        "storage": {"used": _storage_used(db, user.id), "used_bytes": sum(f.size or 0 for f in
                     db.query(CloudFile).filter(CloudFile.user_id == user.id).all()),
                    "total": STORAGE_TOTAL_GB},
        "items": items,
    }


# ─── POST /cloud/folders ───────────────────────────────────────
@router.post("/folders")
def create_folder(body: FolderCreate, request: Request, db: Session = Depends(get_db)):
    user = _require_user(request, db)
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="ชื่อโฟลเดอร์ว่าง")
    if body.parent_id is not None:
        parent = db.query(CloudFolder).filter(
            CloudFolder.id == body.parent_id, CloudFolder.user_id == user.id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="ไม่พบโฟลเดอร์แม่")
    f = CloudFolder(user_id=user.id, parent_id=body.parent_id, name=body.name.strip())
    db.add(f)
    db.commit()
    db.refresh(f)
    return {"id": f.id, "name": f.name}


# ─── POST /cloud/upload ────────────────────────────────────────
@router.post("/upload")
async def upload_file(request: Request,
                      file: UploadFile = File(...),
                      folder_id: int | None = Form(None),
                      db: Session = Depends(get_db)):
    user = _require_user(request, db)
    if folder_id is not None:
        folder = db.query(CloudFolder).filter(
            CloudFolder.id == folder_id, CloudFolder.user_id == user.id).first()
        if not folder:
            raise HTTPException(status_code=404, detail="ไม่พบโฟลเดอร์")

    # quota check
    used = _storage_used(db, user.id)
    content = await file.read()
    if used + len(content) / (1024 ** 3) > STORAGE_TOTAL_GB:
        raise HTTPException(status_code=400, detail="พื้นที่จัดเก็บเต็ม")

    # เก็บไฟล์: uploads/<user_id>/<uuid>_<safe_name>
    safe_name = os.path.basename(file.filename or "file").replace("/", "_")
    disk_name = f"{uuid.uuid4().hex[:10]}_{safe_name}"
    dest = os.path.join(_user_dir(user.id), disk_name)
    with open(dest, "wb") as out:
        out.write(content)

    cf = CloudFile(user_id=user.id, folder_id=folder_id, name=file.filename or safe_name,
                   size=len(content), path=os.path.join(str(user.id), disk_name))
    db.add(cf)
    db.commit()
    db.refresh(cf)
    return {"id": cf.id, "name": cf.name, "size": cf.size}


# ─── GET /cloud/download/{file_id} ─────────────────────────────
@router.get("/download/{file_id}")
def download_file(file_id: int, request: Request, db: Session = Depends(get_db)):
    user = _require_user(request, db)
    f = db.query(CloudFile).filter(CloudFile.id == file_id,
                                   CloudFile.user_id == user.id).first()
    if not f:
        raise HTTPException(status_code=404, detail="ไม่พบไฟล์")
    full = os.path.join(UPLOAD_ROOT, f.path)
    if not os.path.isfile(full):
        raise HTTPException(status_code=410, detail="ไฟล์ถูกย้ายหรือลบไปแล้ว")
    return FileResponse(full, filename=f.name)


# ─── DELETE /cloud/items/{id} — โฟลเดอร์ (พร้อมไฟล์ในนั้น) หรือ ไฟล์ ──
@router.delete("/items/{item_id}")
def delete_item(item_id: int, request: Request, type: str | None = None, db: Session = Depends(get_db)):
    """type=folder|file — id ของโฟลเดอร์กับไฟล์มาจากคนละตาราง จึงซ้ำกันได้
    ถ้าไม่ระบุ type จะลองโฟลเดอร์ก่อน (แบบเดิม) — หน้าเว็บส่ง type มาเสมอ"""
    user = _require_user(request, db)
    if type not in (None, "", "folder", "file"):
        raise HTTPException(status_code=400, detail="type ต้องเป็น folder หรือ file")

    folder = None
    if type != "file":
        folder = db.query(CloudFolder).filter(CloudFolder.id == item_id,
                                              CloudFolder.user_id == user.id).first()
    if folder:
        # ลบไฟล์ในโฟลเดอร์ + โฟลเดอร์ลูก (recursive)
        def _rm(folders: list[CloudFolder]):
            for fo in folders:
                files = db.query(CloudFile).filter(CloudFile.folder_id == fo.id).all()
                for fl in files:
                    p = os.path.join(UPLOAD_ROOT, fl.path)
                    if os.path.isfile(p):
                        os.remove(p)
                    db.delete(fl)
                children = db.query(CloudFolder).filter(
                    CloudFolder.parent_id == fo.id).all()
                _rm(children)
                db.delete(fo)
        _rm([folder])
        db.commit()
        return {"ok": True}

    # เป็นไฟล์
    f = None
    if type != "folder":
        f = db.query(CloudFile).filter(CloudFile.id == item_id,
                                       CloudFile.user_id == user.id).first()
    if f:
        p = os.path.join(UPLOAD_ROOT, f.path)
        if os.path.isfile(p):
            os.remove(p)
        db.delete(f)
        db.commit()
        return {"ok": True}

    raise HTTPException(status_code=404, detail="ไม่พบรายการ")
