"""Nav System - FastAPI Application"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import init_db, get_db, async_session
from app.services.auth import AuthService
from app.services.log import LogService
from app.routers import (
    auth_router, links_router, categories_router,
    articles_router, folders_router, settings_router,
    logs_router, favicon_router
)
from app.routers.settings import get_site_settings

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    auth_service = AuthService()
    security_errors = auth_service.validate_config()
    if security_errors:
        msg = "安全配置错误，服务无法启动:\n" + "\n".join(f"- {e}" for e in security_errors)
        raise RuntimeError(msg)
    await init_db()
    yield
    # Shutdown

app = FastAPI(title="个人主页导航系统", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")
templates = Jinja2Templates(directory=str(settings.templates_dir))

# Include routers
app.include_router(auth_router)
app.include_router(links_router)
app.include_router(categories_router)
app.include_router(articles_router)
app.include_router(folders_router)
app.include_router(settings_router)
app.include_router(logs_router)
app.include_router(favicon_router)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

# Page routes
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Navigation homepage"""
    async with async_session() as db:
        log_service = LogService(db)
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")
        await log_service.record_visit(client_ip, "/", user_agent)
        await db.commit()
        site_settings = await get_site_settings(db)
    return templates.TemplateResponse("index.html", {"request": request, "settings": site_settings})

@app.get("/articles", response_class=HTMLResponse)
async def articles_page(request: Request):
    """Articles list page"""
    async with async_session() as db:
        log_service = LogService(db)
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")
        await log_service.record_visit(client_ip, "/articles", user_agent)
        await db.commit()
        site_settings = await get_site_settings(db)
    return templates.TemplateResponse("article.html", {"request": request, "settings": site_settings})

@app.get("/articles/{path:path}", response_class=HTMLResponse)
async def article_page(request: Request, path: str):
    """Article detail page"""
    async with async_session() as db:
        log_service = LogService(db)
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")
        await log_service.record_visit(client_ip, f"/articles/{path}", user_agent)
        await db.commit()
        site_settings = await get_site_settings(db)
    return templates.TemplateResponse("article.html", {"request": request, "path": path, "settings": site_settings})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
