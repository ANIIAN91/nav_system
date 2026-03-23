"""Nav System - FastAPI application."""

import asyncio
import logging
from contextlib import asynccontextmanager
from contextlib import suppress

from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.database import async_session, check_db_connection
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
from app.services.auth import CredentialService
from app.services.log import LogService, run_log_cleanup_job
from app.services.settings import SettingsService

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    credential_service = CredentialService()
    security_errors = credential_service.validate_config()
    if security_errors:
        msg = "安全配置错误，服务无法启动:\n" + "\n".join(f"- {error}" for error in security_errors)
        raise RuntimeError(msg)
    await check_db_connection()
    cleanup_task = _start_log_cleanup_task()
    try:
        if cleanup_task is not None:
            await _run_log_cleanup_once("startup")
        yield
    finally:
        if cleanup_task is not None:
            cleanup_task.cancel()
            with suppress(asyncio.CancelledError):
                await cleanup_task


app = FastAPI(title="个人主页导航系统", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request, call_next):
    """Attach baseline security headers."""
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data: https:; connect-src 'self'"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")
templates = Jinja2Templates(directory=str(settings.templates_dir))

app.include_router(auth_router)
app.include_router(links_router)
app.include_router(categories_router)
app.include_router(articles_router)
app.include_router(folders_router)
app.include_router(settings_router)
app.include_router(logs_router)
app.include_router(favicon_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, background_tasks: BackgroundTasks):
    """Navigation homepage."""
    background_tasks.add_task(_record_page_visit, _client_ip(request), "/", request.headers.get("user-agent", ""))
    async with async_session() as db:
        site_settings = await SettingsService(db).get_public_settings()
    return templates.TemplateResponse("index.html", {"request": request, "settings": site_settings})


@app.get("/articles", response_class=HTMLResponse)
async def articles_page(request: Request, background_tasks: BackgroundTasks):
    """Articles list page."""
    background_tasks.add_task(_record_page_visit, _client_ip(request), "/articles", request.headers.get("user-agent", ""))
    async with async_session() as db:
        site_settings = await SettingsService(db).get_public_settings()
    return templates.TemplateResponse("article.html", {"request": request, "settings": site_settings})


@app.get("/articles/{path:path}", response_class=HTMLResponse)
async def article_page(request: Request, path: str, background_tasks: BackgroundTasks):
    """Article detail page."""
    background_tasks.add_task(
        _record_page_visit,
        _client_ip(request),
        f"/articles/{path}",
        request.headers.get("user-agent", ""),
    )
    async with async_session() as db:
        site_settings = await SettingsService(db).get_public_settings()
    return templates.TemplateResponse("article.html", {"request": request, "path": path, "settings": site_settings})


async def _record_page_visit(client_ip: str, path: str, user_agent: str) -> None:
    """Persist page visit logs outside the template render path."""
    async with async_session() as db:
        await LogService(db).record_visit(client_ip, path, user_agent)
        await db.commit()


def _client_ip(request: Request) -> str:
    """Extract a best-effort client IP."""
    return request.client.host if request.client else "unknown"


def _start_log_cleanup_task() -> asyncio.Task | None:
    """Start the periodic log cleanup loop when enabled."""
    if not settings.enable_log_cleanup:
        return None
    if settings.log_cleanup_interval_seconds <= 0:
        logger.warning("Periodic log cleanup disabled because LOG_CLEANUP_INTERVAL_SECONDS <= 0")
        return None
    return asyncio.create_task(_run_periodic_log_cleanup())


async def _run_periodic_log_cleanup() -> None:
    """Run log retention cleanup on a fixed interval."""
    while True:
        await asyncio.sleep(settings.log_cleanup_interval_seconds)
        await _run_log_cleanup_once("scheduled")


async def _run_log_cleanup_once(reason: str) -> None:
    """Run one log cleanup cycle and report the result."""
    try:
        summary = await run_log_cleanup_job(async_session)
    except Exception:
        logger.exception("Log cleanup failed", extra={"reason": reason})
        return

    logger.info(
        "Log cleanup completed",
        extra={
            "reason": reason,
            "deleted_visits": summary["deleted_visits"],
            "deleted_updates": summary["deleted_updates"],
            "remaining_visits": summary["remaining_visits"],
            "remaining_updates": summary["remaining_updates"],
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
