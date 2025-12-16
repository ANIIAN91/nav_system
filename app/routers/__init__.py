"""API routers"""
from app.routers.auth import router as auth_router
from app.routers.links import router as links_router
from app.routers.categories import router as categories_router
from app.routers.articles import router as articles_router
from app.routers.folders import router as folders_router
from app.routers.settings import router as settings_router
from app.routers.logs import router as logs_router
from app.routers.favicon import router as favicon_router

__all__ = [
    "auth_router", "links_router", "categories_router",
    "articles_router", "folders_router", "settings_router",
    "logs_router", "favicon_router"
]
