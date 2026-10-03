"""NRW Media model — รูปภาพที่แนบกับเนื้อหาทุกประเภท (แบบเดียวกันทุกระบบ, ไม่ต้องแก้ตารางเดิม)"""
from sqlalchemy import Column, Integer, String
from app.database import Base


class ItemImage(Base):
    __tablename__ = "item_images"

    id       = Column(Integer, primary_key=True)
    kind     = Column(String(30), nullable=False, index=True)    # product / listing / course / event / creator / job ...
    item_id  = Column(Integer, nullable=False, index=True)
    position = Column(Integer, nullable=False, default=0)
    url      = Column(String(500), nullable=False)
