"""NRW Wallet models — balance + transactions per user"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Numeric
from sqlalchemy.sql import func
from app.database import Base


class Wallet(Base):
    __tablename__ = "wallets"

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    balance    = Column(Numeric(12, 2), default=0)   # บาท
    token      = Column(Integer, default=0)          # โทเคน
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type       = Column(String(20), nullable=False)   # topup / withdraw / token
    amount     = Column(Numeric(12, 2), nullable=False)  # + = เข้า, - = ออก
    desc       = Column(String(200), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class WalletRequest(Base):
    """คำขอเติม/ถอนเงิน — รอผู้ดูแลอนุมัติ (ยังไม่มี payment gateway)"""
    __tablename__ = "wallet_requests"

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type       = Column(String(20), nullable=False)        # topup / withdraw
    amount     = Column(Numeric(12, 2), nullable=False)
    desc       = Column(String(200), nullable=False, default="")  # ช่องทาง / เลขบัญชี / อ้างอิงสลิป
    status     = Column(String(20), nullable=False, default="pending", index=True)  # pending/approved/rejected
    decided_by = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    decided_at = Column(DateTime(timezone=True), nullable=True)


class TokenTransaction(Base):
    """ประวัติโทเคน — ได้จากการซื้อ, โอน, แลกเป็นเงิน"""
    __tablename__ = "token_transactions"

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount     = Column(Integer, nullable=False)           # + ได้ / - ใช้
    kind       = Column(String(20), nullable=False)        # earn / transfer_in / transfer_out / redeem / admin
    note       = Column(String(200), nullable=False, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
