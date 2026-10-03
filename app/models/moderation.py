"""NRW Moderation model — คิวอนุมัติเนื้อหาที่สมาชิกลง (1 แถวต่อ 1 ชิ้น)

ไม่มีแถว = เนื้อหาเก่า/ของผู้ดูแล → ถือว่าอนุมัติแล้ว"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base


class Moderation(Base):
    __tablename__ = "moderation"
    __table_args__ = (UniqueConstraint("kind", "item_id", name="uq_moderation_item"),)

    id         = Column(Integer, primary_key=True)
    kind       = Column(String(30), nullable=False, index=True)      # post / product / listing / ...
    item_id    = Column(Integer, nullable=False, index=True)
    owner_id   = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status     = Column(String(20), nullable=False, default="pending", index=True)   # pending/approved/rejected
    reason     = Column(String(300), nullable=False, default="")
    decided_by = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    decided_at = Column(DateTime(timezone=True), nullable=True)
