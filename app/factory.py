"""Application factory and bootstrap orchestration."""

import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.router import register_api_router
from app.config import get_settings
from app.database import check_db_connection, get_async_session_factory
from app.services.auth import CredentialService, reset_auth_service_state
from app.services.log import run_log_cleanup_job
from app.web.pages import register_page_router

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")
    reset_auth_service_state()
    settings = get_settings()
    ensure_runtime_directories(settings.base_dir, settings.data_dir, settings.articles_dir, settings.static_dir / "icons")

    app = FastAPI(title="个人主页导航系统", lifespan=build_lifespan())
    app.state.settings = settings
    app.state.templates = Jinja2Templates(directory=str(settings.templates_dir))
    app.state.session_factory = get_async_session_factory()

    app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")
    register_middlewares(app)
    register_api_router(app)
    register_page_router(app)
    return app


def register_middlewares(app: FastAPI) -> None:
    """Register application middlewares."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_security_headers(request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data: https:; connect-src 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


def build_lifespan():
    """Build the FastAPI lifespan handler."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await startup_jobs(app)
        try:
            yield
        finally:
            await shutdown_jobs(app)

    return lifespan


async def startup_jobs(app: FastAPI) -> None:
    """Run startup validation and background job wiring."""
    settings = app.state.settings
    credential_service = CredentialService(settings=settings)
    security_errors = credential_service.validate_config()
    if security_errors:
        msg = "安全配置错误，服务无法启动:\n" + "\n".join(f"- {error}" for error in security_errors)
        raise RuntimeError(msg)

    await check_db_connection()
    cleanup_task = _start_log_cleanup_task(app)
    app.state.log_cleanup_task = cleanup_task
    if cleanup_task is not None:
        await _run_log_cleanup_once(app, "startup")


async def shutdown_jobs(app: FastAPI) -> None:
    """Tear down background jobs."""
    cleanup_task = getattr(app.state, "log_cleanup_task", None)
    if cleanup_task is not None:
        cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup_task


def ensure_runtime_directories(*paths: Path) -> None:
    """Create runtime directories outside the configuration layer."""
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def _start_log_cleanup_task(app: FastAPI) -> asyncio.Task | None:
    settings = app.state.settings
    if not settings.enable_log_cleanup:
        return None
    if settings.log_cleanup_interval_seconds <= 0:
        logger.warning("Periodic log cleanup disabled because LOG_CLEANUP_INTERVAL_SECONDS <= 0")
        return None
    return asyncio.create_task(_run_periodic_log_cleanup(app))


async def _run_periodic_log_cleanup(app: FastAPI) -> None:
    while True:
        await asyncio.sleep(app.state.settings.log_cleanup_interval_seconds)
        await _run_log_cleanup_once(app, "scheduled")


async def _run_log_cleanup_once(app: FastAPI, reason: str) -> None:
    try:
        summary = await run_log_cleanup_job(app.state.session_factory)
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
