"""Authentication routes."""

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import SESSION_COOKIE_NAME, require_auth, security, session_token
from app.config import get_settings
from app.database import get_db
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth import (
    CredentialService,
    TokenService,
    get_credential_service,
    get_token_service,
)
from app.utils.security import create_access_token

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

def _is_https(request: Request) -> bool:
    forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",")[0].strip()
    return request.url.scheme == "https" or forwarded_proto == "https"


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    req: Request,
    response: Response,
    credential_service: CredentialService = Depends(get_credential_service),
):
    """User login; also sets the HttpOnly browser session cookie."""
    client_ip = req.client.host if req.client else "unknown"
    result = credential_service.authenticate(request.username, request.password, client_ip)
    if "error" in result:
        raise HTTPException(status_code=result["status"], detail=result["error"])

    response.set_cookie(
        SESSION_COOKIE_NAME,
        result["access_token"],
        # 勾选“保持登录”时 Cookie 与 token 同寿命，否则关闭浏览器即失效
        max_age=get_settings().access_token_expire_minutes * 60 if request.remember else None,
        httponly=True,
        samesite="lax",
        secure=_is_https(req),
        path="/",
    )
    return result


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
    token_service: TokenService = Depends(get_token_service),
):
    """User logout with server-side token revoke."""
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    if credentials is not None:
        token, from_cookie = credentials.credentials, False
    else:
        token, from_cookie = session_token(request), True
    if token is None:
        return {"message": "已登出"}

    revoked = await token_service.revoke_token(token, db)
    if not revoked:
        if from_cookie:
            # 已失效的会话 Cookie 直接清除即可
            return {"message": "已登出"}
        raise HTTPException(status_code=401, detail="Token 无效或已过期")

    await db.commit()
    return {"message": "已登出"}


@router.get("/me")
async def get_me(username: str = Depends(require_auth)):
    """Get current user info."""
    return {"username": username}


@router.post("/token", response_model=TokenResponse)
async def create_api_token(username: str = Depends(require_auth)):
    """Issue a bearer token for the Obsidian plugin or sync scripts."""
    access_token = create_access_token(
        data={"sub": username},
        expires_delta=timedelta(minutes=get_settings().access_token_expire_minutes),
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/cleanup-tokens")
async def cleanup_expired_tokens(
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
    token_service: TokenService = Depends(get_token_service),
):
    """Clean up expired tokens from blacklist."""
    deleted_count = await token_service.cleanup_expired_tokens(db)
    await db.commit()
    return {"message": f"已清理 {deleted_count} 个过期 token", "deleted_count": deleted_count}
