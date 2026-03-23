"""Pydantic schemas."""

from app.schemas.article import (
    ArticleDetailResponse,
    ArticleListResponse,
    ArticleMutationResponse,
    ArticleSyncRequest,
    ArticleUpdateRequest,
)
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse
from app.schemas.folder import FolderListResponse, FolderRenameRequest, FolderSummary
from app.schemas.link import LinkCreate, LinkResponse, LinksData, LinkUpdate
from app.schemas.site_settings import (
    SiteSettingsResponse,
    SiteSettingsUpdateRequest,
    SiteSettingsUpdateResponse,
)

__all__ = [
    "LoginRequest",
    "TokenResponse",
    "LinkCreate",
    "LinkUpdate",
    "LinkResponse",
    "LinksData",
    "CategoryCreate",
    "CategoryUpdate",
    "CategoryResponse",
    "ArticleDetailResponse",
    "ArticleListResponse",
    "ArticleMutationResponse",
    "ArticleSyncRequest",
    "ArticleUpdateRequest",
    "FolderListResponse",
    "FolderRenameRequest",
    "FolderSummary",
    "SiteSettingsResponse",
    "SiteSettingsUpdateRequest",
    "SiteSettingsUpdateResponse",
]
