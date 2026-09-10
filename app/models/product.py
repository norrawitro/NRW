"""NRW Product model — ร้านค้า"""
from sqlalchemy import Column, Integer, String, Float, Text, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base

class Product(Base):
    __tablename__ = "products"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(200), nullable=False)
    description = Column(Text, default="")
    price       = Column(Float, nullable=False)
    stock       = Column(Integer, default=0)
    image_url   = Column(String(500), default="")
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
