"""NRW Admin Router — จัดการข้อมูล (ต้อง login)"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import verify_admin

router = APIRouter()


@router.get("/")
async def admin_home(username: str = Depends(verify_admin)):
    """Admin home (ต้อง login)"""
    return {"module": "Admin", "status": "ok", "user": username}


@router.get("/dashboard")
async def dashboard(
    db: Session = Depends(get_db),
    username: str = Depends(verify_admin)
):
    """ภาพรวมระบบ (ต้อง login)"""
    # TODO: query จริงจาก DB
    return {
        "user": username,
        "stats": {
            "users": 0,
            "orders": 0,
            "sensors": 0,
            "active_connections": 0
        }
    }


@router.get("/users")
async def list_users(
    db: Session = Depends(get_db),
    username: str = Depends(verify_admin)
):
    """รายการ users ทั้งหมด"""
    # TODO: query จาก DB
    return {"users": []}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(verify_admin)
):
    """ลบ user"""
    # TODO: implement
    return {"deleted": user_id, "by": username}
