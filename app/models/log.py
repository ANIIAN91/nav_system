"""Log models"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from app.database import Base

class VisitLog(Base):
    __tablename__ = "visit_logs"

    id = Column(Integer, primary_key=True, index=True)
    ip = Column(String(45), nullable=True)
    path = Column(String(500), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_visit_logs_created_at", created_at.desc()),
    )

class UpdateLog(Base):
    __tablename__ = "update_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(50), nullable=True)
    target_type = Column(String(50), nullable=True)
    target_name = Column(String(200), nullable=True)
    details = Column(Text, nullable=True)
    username = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_update_logs_created_at", created_at.desc()),
    )
