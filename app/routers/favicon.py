"""Favicon routes"""
from fastapi import APIRouter, HTTPException, Depends

from app.schemas.link import FaviconRequest
from app.utils.favicon import fetch_favicon
from app.routers.auth import require_auth

router = APIRouter(prefix="/api/v1/favicon", tags=["favicon"])

@router.post("/fetch")
async def get_favicon(
    request: FaviconRequest,
    username: str = Depends(require_auth)
):
    """Fetch favicon from website and save"""
    result = await fetch_favicon(request.url)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["message"])
    return result
