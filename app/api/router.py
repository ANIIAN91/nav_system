"""API router registration."""

from fastapi import FastAPI

from app.routers import (
    articles_router,
    auth_router,
    categories_router,
    favicon_router,
    folders_router,
    links_router,
    logs_router,
    settings_router,
)


def register_api_router(app: FastAPI) -> None:
    """Register all API routers on the application."""
    app.include_router(auth_router)
    app.include_router(links_router)
    app.include_router(categories_router)
    app.include_router(articles_router)
    app.include_router(folders_router)
    app.include_router(settings_router)
    app.include_router(logs_router)
    app.include_router(favicon_router)
