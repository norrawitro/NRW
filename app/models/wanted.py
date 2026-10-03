"""NRW Wanted models — ประกาศซื้อ: สมาชิกโพสต์ว่าต้องการซื้ออะไร คนที่มีของมายื่นข้อเสนอ"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.database import Base


class WantedPost(Base):
    __tablename__ = "wanted_posts"

    id          = Column(Integer, primary_key=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title       = Column(String(200), nullable=False)
    description = Column(Text, nullable=False, default="")
    budget      = Column(Numeric(12, 2), nullable=False)    # งบสูงสุดที่ยอมจ่าย
    status      = Column(String(20), nullable=False, default="open", index=True)  # open / done / closed
    created_at  = Column(DateTime(timezone=True), server_default=func.now())


class WantedOffer(Base):
    """ข้อเสนอขายจากสมาชิกคนอื่น"""
    __tablename__ = "wanted_offers"

    id          = Column(Integer, primary_key=True)
    post_id     = Column(Integer, ForeignKey("wanted_posts.id"), nullable=False, index=True)
    seller_id   = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    message     = Column(Text, nullable=False, default="")
    price       = Column(Numeric(12, 2), nullable=False)
    status      = Column(String(20), nullable=False, default="pending")  # pending / accepted / declined
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
