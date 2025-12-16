"""Pydantic schemas"""
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.link import LinkCreate, LinkUpdate, LinkResponse, LinksData
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse
from app.schemas.setting import SiteSettings

__all__ = [
    "LoginRequest", "TokenResponse",
    "LinkCreate", "LinkUpdate", "LinkResponse", "LinksData",
    "CategoryCreate", "CategoryUpdate", "CategoryResponse",
    "SiteSettings"
]
