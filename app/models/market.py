"""NRW Market models — ประกาศขายของมือสอง / ให้เช่า ระหว่างสมาชิก"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.database import Base


class Listing(Base):
    __tablename__ = "market_listings"

    id          = Column(Integer, primary_key=True)
    seller_id   = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    kind        = Column(String(10), nullable=False)        # sale / rent
    title       = Column(String(200), nullable=False)
    description = Column(Text, nullable=False, default="")
    price       = Column(Numeric(12, 2), nullable=False)    # sale = ราคาขาย, rent = ค่าเช่าต่อวัน
    status      = Column(String(20), nullable=False, default="active", index=True)  # active/sold/rented/closed
    created_at  = Column(DateTime(timezone=True), server_default=func.now())


class Deal(Base):
    """การซื้อ/เช่า 1 ครั้ง"""
    __tablename__ = "market_deals"

    id          = Column(Integer, primary_key=True)
    listing_id  = Column(Integer, ForeignKey("market_listings.id"), nullable=False, index=True)
    buyer_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    kind        = Column(String(10), nullable=False)        # sale / rent
    days        = Column(Integer, nullable=False, default=0)
    total       = Column(Numeric(12, 2), nullable=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    returned_at = Column(DateTime(timezone=True), nullable=True)
