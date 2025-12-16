"""Setting schemas"""
from typing import Optional, List
from pydantic import BaseModel

class SiteSettings(BaseModel):
    icp: Optional[str] = ""
    copyright: Optional[str] = ""
    article_page_title: Optional[str] = "文章"
    site_title: Optional[str] = "个人主页导航"
    link_size: Optional[str] = "medium"
    protected_article_paths: Optional[List[str]] = []
    analytics_code: Optional[str] = ""

class ArticleSyncRequest(BaseModel):
    path: str
    content: str
    title: Optional[str] = None
    tags: Optional[List[str]] = []
    frontmatter: Optional[dict] = None

class ArticleUpdateRequest(BaseModel):
    content: str

class FolderRenameRequest(BaseModel):
    new_name: str
