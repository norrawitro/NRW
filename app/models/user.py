"""NRW User model"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id           = Column(Integer, primary_key=True, index=True)
    username     = Column(String(50), unique=True, nullable=False, index=True)
    email        = Column(String(100), unique=True, nullable=False, index=True)
    full_name    = Column(String(100), nullable=False)
    phone        = Column(String(20), nullable=True)
    hashed_pw    = Column(String(200), nullable=False)
    is_admin     = Column(Boolean, default=False)
    is_active    = Column(Boolean, default=True)
    note         = Column(Text, nullable=True)   # admin-only note
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), onupdate=func.now())
