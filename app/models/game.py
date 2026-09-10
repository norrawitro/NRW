"""NRW Game model — player scores & sessions"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from app.database import Base

class Player(Base):
    __tablename__ = "players"

    id         = Column(Integer, primary_key=True, index=True)
    player_id  = Column(String(50), unique=True, nullable=False)
    nickname   = Column(String(100), default="")
    score      = Column(Integer, default=0)
    wins       = Column(Integer, default=0)
    losses     = Column(Integer, default=0)
    is_online  = Column(Boolean, default=False)
    last_seen  = Column(DateTime(timezone=True), server_default=func.now())
