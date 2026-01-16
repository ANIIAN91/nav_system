"""Authentication routes"""
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from datetime import datetime
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete

from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth import AuthService
from app.utils.security import verify_token
from app.database import get_db
from app.models.token_blacklist import TokenBlacklist
from app.config import get_settings

settings = get_settings()

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[str]:
    """Get current user (optional auth)"""
    if credentials is None:
        return None
    return await verify_token(credentials.credentials, db)

async def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> str:
    """Require authentication"""
    if credentials is None:
        raise HTTPException(status_code=401, detail="未登录")
    username = await verify_token(credentials.credentials, db)
    if username is None:
        raise HTTPException(status_code=401, detail="Token 无效或已过期")
    return username

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, req: Request):
    """User login"""
    client_ip = req.client.host if req.client else "unknown"
    auth_service = AuthService()
    result = auth_service.authenticate(request.username, request.password, client_ip)

    if "error" in result:
        raise HTTPException(status_code=result["status"], detail=result["error"])

    return result

@router.post("/logout")
async def logout(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """User logout - revoke token"""
    if credentials is None:
        return {"message": "已登出"}

    try:
        # 解析 token 获取 jti 和过期时间
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        jti = payload.get("jti")
        username = payload.get("sub")
        exp = payload.get("exp")

        if jti and username and exp:
            # 将 token 加入黑名单
            blacklist_entry = TokenBlacklist(
                jti=jti,
                username=username,
                revoked_at=datetime.utcnow(),
                expires_at=datetime.fromtimestamp(exp),
                reason="logout"
            )
            db.add(blacklist_entry)
            await db.commit()
    except Exception:
        # 即使撤销失败也返回成功（客户端会删除 token）
        pass

    return {"message": "已登出"}

@router.get("/me")
async def get_me(username: str = Depends(require_auth)):
    """Get current user info"""
    return {"username": username}

@router.post("/cleanup-tokens")
async def cleanup_expired_tokens(
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Clean up expired tokens from blacklist (admin only)"""
    # 删除已过期的 token
    result = await db.execute(
        delete(TokenBlacklist).where(TokenBlacklist.expires_at < datetime.utcnow())
    )
    await db.commit()
    deleted_count = result.rowcount

    return {
        "message": f"已清理 {deleted_count} 个过期 token",
        "deleted_count": deleted_count
    }
