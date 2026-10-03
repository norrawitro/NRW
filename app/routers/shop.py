"""NRW Shop Router — ร้านค้าออนไลน์"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.product import Product

router = APIRouter()

@router.get("/")
async def shop_home():
    return {"module": "Shop", "status": "ok"}

@router.get("/products")
async def list_products(db: Session = Depends(get_db)):
    """รายการสินค้าทั้งหมด"""
    products = (
        db.query(Product)
        .filter(Product.is_active == True)
        .order_by(Product.created_at.desc())
        .all()
    )
    return {
        "products": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "price": p.price,
                "stock": p.stock,
                "image_url": p.image_url,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in products
        ]
    }

@router.get("/products/{product_id}")
async def get_product(product_id: int, db: Session = Depends(get_db)):
    """ดูสินค้าชิ้นเดียว"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "price": product.price,
        "stock": product.stock,
        "image_url": product.image_url,
        "created_at": product.created_at.isoformat() if product.created_at else None,
    }
