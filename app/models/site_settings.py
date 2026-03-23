"""Typed site settings model."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.config import GITHUB_URL
from app.database import Base


class SiteSettings(Base):
    __tablename__ = "site_settings"

    id = Column(Integer, primary_key=True, default=1)
    site_title = Column(String(255), nullable=False, default="个人主页导航")
    article_page_title = Column(String(255), nullable=False, default="文章")
    icp = Column(String(255), nullable=False, default="")
    copyright = Column(String(255), nullable=False, default="")
    link_size = Column(String(32), nullable=False, default="medium")
    timezone = Column(String(64), nullable=False, default="Asia/Shanghai")
    github_url = Column(String(500), nullable=False, default=GITHUB_URL)
    protected_article_paths_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
