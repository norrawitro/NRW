"""NRW Admin Router — จัดการข้อมูล (ต้อง login)
เข้าถึงได้เฉพาะจาก localhost (127.0.0.1) เท่านั้น
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import verify_admin
from app.models.user import User

router = APIRouter()

def _local_only(request: Request):
    """Block requests ที่ไม่ได้มาจาก localhost"""
    client = request.client.host if request.client else ""
    if client not in ("127.0.0.1", "::1", "localhost"):
        raise HTTPException(status_code=403, detail="เข้าถึงได้เฉพาะจาก localhost")


@router.get("/")
async def admin_home(
    request: Request,
    username: str = Depends(verify_admin)
):
    _local_only(request)
    return {"module": "Admin", "status": "ok", "user": username}


@router.get("/dashboard")
async def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Depends(verify_admin)
):
    _local_only(request)
    total_users  = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    admin_users  = db.query(User).filter(User.is_admin == True).count()
    return {
        "user": username,
        "stats": {
            "total_users":  total_users,
            "active_users": active_users,
            "admin_users":  admin_users,
        }
    }


@router.get("/users")
async def list_users(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Depends(verify_admin)
):
    """รายการสมาชิกทั้งหมด — เข้าถึงได้เฉพาะ localhost"""
    _local_only(request)
    users = db.query(User).order_by(User.created_at.desc()).all()
    return {
        "total": len(users),
        "users": [
            {
                "id":         u.id,
                "username":   u.username,
                "full_name":  u.full_name,
                "email":      u.email,
                "phone":      u.phone,
                "is_admin":   u.is_admin,
                "is_active":  u.is_active,
                "created_at": str(u.created_at),
            }
            for u in users
        ]
    }


@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    username: str = Depends(verify_admin)
):
    _local_only(request)
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="ไม่พบ user")
    return {
        "id": u.id, "username": u.username, "full_name": u.full_name,
        "email": u.email, "phone": u.phone, "is_admin": u.is_admin,
        "is_active": u.is_active, "note": u.note, "created_at": str(u.created_at)
    }


@router.patch("/users/{user_id}/toggle-active")
async def toggle_active(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    username: str = Depends(verify_admin)
):
    """เปิด/ปิด account สมาชิก"""
    _local_only(request)
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="ไม่พบ user")
    u.is_active = not u.is_active
    db.commit()
    return {"id": u.id, "username": u.username, "is_active": u.is_active}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    username: str = Depends(verify_admin)
):
    """ลบ user"""
    _local_only(request)
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="ไม่พบ user")
    db.delete(u)
    db.commit()
    return {"deleted": user_id, "by": username}
