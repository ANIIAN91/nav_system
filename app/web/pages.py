"""Template-backed page routes."""

from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.application.unit_of_work import SqlAlchemyUnitOfWork
from app.application.use_cases.logs import record_page_visit

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, background_tasks: BackgroundTasks):
    """Navigation homepage."""
    _queue_visit(background_tasks, request, "/")
    async with request.app.state.session_factory() as db:
        site_settings = await SqlAlchemyUnitOfWork(db).settings.get_public_settings()
    return request.app.state.templates.TemplateResponse("index.html", {"request": request, "settings": site_settings})


@router.get("/articles")
async def articles_page(request: Request, background_tasks: BackgroundTasks):
    """Legacy articles page route now redirects to the homepage."""
    _queue_visit(background_tasks, request, "/articles")
    return RedirectResponse(url="/", status_code=307)


@router.get("/articles/{path:path}")
async def article_page(request: Request, path: str, background_tasks: BackgroundTasks):
    """Legacy article detail route now redirects to the homepage article sheet."""
    _queue_visit(background_tasks, request, f"/articles/{path}")
    return RedirectResponse(url=f"/?article={quote(path, safe='')}", status_code=307)


def register_page_router(app: FastAPI) -> None:
    """Register page and system routes on the application."""
    app.include_router(router)


def _queue_visit(background_tasks: BackgroundTasks, request: Request, path: str) -> None:
    background_tasks.add_task(
        record_page_visit,
        request.app.state.session_factory,
        _client_ip(request),
        path,
        request.headers.get("user-agent", ""),
    )


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"
