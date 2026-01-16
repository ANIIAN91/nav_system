"""Token blacklist model"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Index
from app.database import Base

class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"

    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String(100), unique=True, nullable=False, index=True)  # JWT ID
    username = Column(String(100), nullable=False)
    revoked_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)  # Token 过期时间
    reason = Column(String(200), nullable=True)  # 撤销原因（如 "logout", "security"）

    __table_args__ = (
        Index("idx_token_blacklist_jti", "jti"),
        Index("idx_token_blacklist_expires_at", "expires_at"),
    )
