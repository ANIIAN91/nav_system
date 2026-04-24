"""Authentication dependencies shared across API routers."""

from typing import Optional

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.auth import TokenService, get_token_service

security = HTTPBearer(auto_error=False)
UNAUTHENTICATED_DETAIL = "未登录"
INVALID_TOKEN_DETAIL = "Token 无效或已过期"


def _has_authorization_header(request: Request) -> bool:
    return bool(request.headers.get("Authorization"))


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
    token_service: TokenService = Depends(get_token_service),
) -> Optional[str]:
    """Resolve the current user when a bearer token is present."""
    if credentials is None:
        if _has_authorization_header(request):
            raise HTTPException(status_code=401, detail=INVALID_TOKEN_DETAIL)
        return None
    username = await token_service.verify_token(credentials.credentials, db)
    if username is None:
        raise HTTPException(status_code=401, detail=INVALID_TOKEN_DETAIL)
    return username


async def require_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
    token_service: TokenService = Depends(get_token_service),
) -> str:
    """Require a valid bearer token and return its subject."""
    if credentials is None:
        detail = INVALID_TOKEN_DETAIL if _has_authorization_header(request) else UNAUTHENTICATED_DETAIL
        raise HTTPException(status_code=401, detail=detail)
    username = await token_service.verify_token(credentials.credentials, db)
    if username is None:
        raise HTTPException(status_code=401, detail=INVALID_TOKEN_DETAIL)
    return username
