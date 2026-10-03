"""NRW ช่วงที่ 4 models — วิดีโอ, เกม, กิจกรรม/ตั๋ว, ครีเอเตอร์ VIP, อุปกรณ์ IoT, สุขภาพ"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text, Boolean, Date
from sqlalchemy.sql import func
from app.database import Base


class Video(Base):
    __tablename__ = "videos"
    id          = Column(Integer, primary_key=True)
    owner_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title       = Column(String(200), nullable=False)
    description = Column(Text, nullable=False, default="")
    path        = Column(String(500), nullable=False)      # ใต้ uploads/videos/
    size        = Column(Integer, nullable=False, default=0)
    views       = Column(Integer, nullable=False, default=0)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())


class GameScore(Base):
    __tablename__ = "game_scores"
    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    game       = Column(String(30), nullable=False, index=True)
    score      = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Event(Base):
    __tablename__ = "events"
    id           = Column(Integer, primary_key=True)
    organizer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title        = Column(String(200), nullable=False)
    description  = Column(Text, nullable=False, default="")
    starts_at    = Column(DateTime(timezone=True), nullable=False)
    place        = Column(String(300), nullable=False, default="")   # สถานที่ หรือ ลิงก์ออนไลน์
    price        = Column(Numeric(12, 2), nullable=False, default=0)
    capacity     = Column(Integer, nullable=False, default=50)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())


class Ticket(Base):
    __tablename__ = "event_tickets"
    id            = Column(Integer, primary_key=True)
    event_id      = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    user_id       = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    code          = Column(String(12), nullable=False, unique=True)
    checked_in_at = Column(DateTime(timezone=True), nullable=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())


class CreatorPage(Base):
    __tablename__ = "creator_pages"
    id            = Column(Integer, primary_key=True)
    user_id       = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    bio           = Column(Text, nullable=False, default="")
    monthly_price = Column(Numeric(12, 2), nullable=False)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())


class CreatorPost(Base):
    __tablename__ = "creator_posts"
    id         = Column(Integer, primary_key=True)
    creator_id = Column(Integer, ForeignKey("creator_pages.id"), nullable=False, index=True)
    title      = Column(String(200), nullable=False)
    body       = Column(Text, nullable=False, default="")
    vip_only   = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Subscription(Base):
    __tablename__ = "creator_subscriptions"
    id         = Column(Integer, primary_key=True)
    creator_id = Column(Integer, ForeignKey("creator_pages.id"), nullable=False, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)


class IoTDevice(Base):
    """อุปกรณ์ของสมาชิก — ESP32 ส่งข้อมูลด้วย header X-Device-Key ของตัวเอง"""
    __tablename__ = "iot_devices"
    id         = Column(Integer, primary_key=True)
    owner_id   = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    device_id  = Column(String(50), nullable=False, unique=True)
    name       = Column(String(100), nullable=False)
    key_hash   = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class IoTCommand(Base):
    __tablename__ = "iot_commands"
    id           = Column(Integer, primary_key=True)
    device_id    = Column(String(50), nullable=False, index=True)
    command      = Column(String(200), nullable=False)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())


class HealthLog(Base):
    __tablename__ = "health_logs"
    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    day        = Column(Date, nullable=False, index=True)
    activity   = Column(String(50), nullable=False)
    minutes    = Column(Integer, nullable=False, default=0)
    steps      = Column(Integer, nullable=False, default=0)
    tokens     = Column(Integer, nullable=False, default=0)       # โทเคนที่ได้จากรายการนี้
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class HealthEvidence(Base):
    """รูปหลักฐานการออกกำลังกาย (1 รูปต่อ 1 รายการ) — ไฟล์อยู่ uploads/health/"""
    __tablename__ = "health_evidence"
    log_id = Column(Integer, ForeignKey("health_logs.id"), primary_key=True)
    path   = Column(String(300), nullable=False)
