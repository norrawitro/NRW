"""NRW Shop models — ออเดอร์ + รายการสินค้าในออเดอร์ + ประวัติการขนส่ง"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.database import Base

ORDER_STATUSES = ["paid", "packed", "shipped", "delivered", "cancelled"]
ORDER_STATUS_LABELS = {"paid": "ชำระแล้ว", "packed": "แพ็กแล้ว", "shipped": "ส่งแล้ว",
                       "delivered": "ได้รับแล้ว", "cancelled": "ยกเลิก"}


class Order(Base):
    __tablename__ = "orders"

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    total      = Column(Numeric(12, 2), nullable=False)
    status     = Column(String(20), nullable=False, default="paid", index=True)
    address    = Column(Text, nullable=False, default="")
    tracking   = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class OrderItem(Base):
    __tablename__ = "order_items"

    id         = Column(Integer, primary_key=True)
    order_id   = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    name       = Column(String(200), nullable=False)      # ชื่อ ณ ตอนซื้อ
    price      = Column(Numeric(12, 2), nullable=False)   # ราคา ณ ตอนซื้อ
    qty        = Column(Integer, nullable=False)


class ShipmentEvent(Base):
    """เส้นทางพัสดุ — 1 แถวต่อการเปลี่ยนสถานะ"""
    __tablename__ = "shipment_events"

    id         = Column(Integer, primary_key=True)
    order_id   = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    status     = Column(String(20), nullable=False)
    note       = Column(String(200), nullable=False, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ProductSeller(Base):
    """สินค้าที่สมาชิกลงขายเอง (สินค้าที่ไม่มีแถวนี้ = สินค้าของแพลตฟอร์ม ลงโดยผู้ดูแล)"""
    __tablename__ = "product_sellers"

    product_id = Column(Integer, ForeignKey("products.id"), primary_key=True)
    seller_id  = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)


class OrderSeller(Base):
    """ผู้ขายของออเดอร์ — เงินพักไว้กับระบบจนผู้ซื้อได้รับสินค้า แล้วจึงโอนให้ผู้ขาย (paid_out)"""
    __tablename__ = "order_sellers"

    order_id  = Column(Integer, ForeignKey("orders.id"), primary_key=True)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    paid_out  = Column(Integer, nullable=False, default=0)    # 0/1
