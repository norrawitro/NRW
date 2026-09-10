"""NRW Shop Router — ร้านค้าออนไลน์"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db

router = APIRouter()

@router.get("/")
async def shop_home():
    return {"module": "Shop", "status": "ok"}

@router.get("/products")
async def list_products(db: Session = Depends(get_db)):
    """รายการสินค้าทั้งหมด"""
    # TODO: query จาก DB
    return {"products": []}

@router.get("/products/{product_id}")
async def get_product(product_id: int, db: Session = Depends(get_db)):
    """ดูสินค้าชิ้นเดียว"""
    return {"product_id": product_id}
