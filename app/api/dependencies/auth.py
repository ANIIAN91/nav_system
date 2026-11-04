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

# 浏览器使用 HttpOnly Cookie 会话；插件和脚本继续使用 Bearer Token
SESSION_COOKIE_NAME = "nav_session"
# Cookie 会话的写请求必须带此请求头，跨站页面无法在不触发 CORS 预检的情况下添加
CSRF_HEADER_NAME = "X-Nav-Request"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def _has_authorization_header(request: Request) -> bool:
    return bool(request.headers.get("Authorization"))


def session_token(request: Request) -> Optional[str]:
    """Return the browser session token from the cookie, if any."""
    return request.cookies.get(SESSION_COOKIE_NAME) or None


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
    token_service: TokenService = Depends(get_token_service),
) -> Optional[str]:
    """Resolve the current user from a bearer token or the session cookie."""
    if credentials is None:
        if _has_authorization_header(request):
            raise HTTPException(status_code=401, detail=INVALID_TOKEN_DETAIL)
        cookie_token = session_token(request)
        if cookie_token is None:
            return None
        # 过期的会话 Cookie 按未登录处理，避免公开页面报错
        return await token_service.verify_token(cookie_token, db)
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
    """Require a valid bearer token or session cookie and return its subject."""
    if credentials is not None:
        token = credentials.credentials
    elif _has_authorization_header(request):
        raise HTTPException(status_code=401, detail=INVALID_TOKEN_DETAIL)
    else:
        token = session_token(request)
        if token is None:
            raise HTTPException(status_code=401, detail=UNAUTHENTICATED_DETAIL)
        if request.method not in SAFE_METHODS and request.headers.get(CSRF_HEADER_NAME) != "1":
            raise HTTPException(status_code=403, detail=f"缺少请求头 {CSRF_HEADER_NAME}")
    username = await token_service.verify_token(token, db)
    if username is None:
        raise HTTPException(status_code=401, detail=INVALID_TOKEN_DETAIL)
    return username
