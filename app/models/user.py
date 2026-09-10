"""NRW User model"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, index=True)
    username   = Column(String(50), unique=True, nullable=False)
    email      = Column(String(100), unique=True, nullable=False)
    hashed_pw  = Column(String(200), nullable=False)
    is_admin   = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
