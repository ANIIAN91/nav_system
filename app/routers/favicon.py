"""Favicon routes."""

from fastapi import APIRouter, Depends

from app.api.dependencies.auth import require_auth
from app.api.http import raise_http_error
from app.application.errors import ApplicationError
from app.application.use_cases.assets import FetchFaviconUseCase
from app.schemas.link import FaviconRequest

router = APIRouter(prefix="/api/v1/favicon", tags=["favicon"])


@router.post("/fetch")
async def get_favicon(
    request: FaviconRequest,
    username: str = Depends(require_auth),
):
    """Fetch favicon from website and save it."""
    try:
        return await FetchFaviconUseCase().execute(request.url)
    except ApplicationError as exc:
        raise_http_error(exc)
