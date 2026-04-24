"""Authentication routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_auth, security
from app.database import get_db
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth import (
    CredentialService,
    TokenService,
    get_credential_service,
    get_token_service,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    req: Request,
    credential_service: CredentialService = Depends(get_credential_service),
):
    """User login."""
    client_ip = req.client.host if req.client else "unknown"
    result = credential_service.authenticate(request.username, request.password, client_ip)
    if "error" in result:
        raise HTTPException(status_code=result["status"], detail=result["error"])
    return result


@router.post("/logout")
async def logout(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
    token_service: TokenService = Depends(get_token_service),
):
    """User logout with server-side token revoke."""
    if credentials is None:
        return {"message": "已登出"}

    revoked = await token_service.revoke_token(credentials.credentials, db)
    if not revoked:
        raise HTTPException(status_code=401, detail="Token 无效或已过期")

    await db.commit()
    return {"message": "已登出"}


@router.get("/me")
async def get_me(username: str = Depends(require_auth)):
    """Get current user info."""
    return {"username": username}


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
