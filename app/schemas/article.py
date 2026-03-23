"""Article schemas."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class ArticleSyncRequest(BaseModel):
    path: str
    content: str
    title: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    frontmatter: Optional[dict[str, Any]] = None


class ArticleUpdateRequest(BaseModel):
    content: str


class ArticleSummary(BaseModel):
    path: str
    title: str
    category: Optional[str] = None
    protected: bool = False
    created_time: float


class ArticleListResponse(BaseModel):
    articles: list[ArticleSummary] = Field(default_factory=list)


class ArticleDetailResponse(BaseModel):
    path: str
    content: str
    html: str


class ArticleMutationResponse(BaseModel):
    message: str
    path: str
    title: Optional[str] = None
