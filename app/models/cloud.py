"""NRW Cloud models — per-user folders + files"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class CloudFolder(Base):
    __tablename__ = "cloud_folders"

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    parent_id  = Column(Integer, ForeignKey("cloud_folders.id"), nullable=True)  # NULL = root
    name       = Column(String(200), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CloudFile(Base):
    __tablename__ = "cloud_files"

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    folder_id  = Column(Integer, ForeignKey("cloud_folders.id"), nullable=True)  # NULL = root
    name       = Column(String(300), nullable=False)
    size       = Column(Integer, default=0)          # bytes
    path       = Column(String(500), nullable=False)  # relative path on disk
    created_at = Column(DateTime(timezone=True), server_default=func.now())
