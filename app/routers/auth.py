"""Authentication routes"""
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth import AuthService
from app.utils.security import verify_token

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """Get current user (optional auth)"""
    if credentials is None:
        return None
    return verify_token(credentials.credentials)

async def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """Require authentication"""
    if credentials is None:
        raise HTTPException(status_code=401, detail="未登录")
    username = verify_token(credentials.credentials)
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
async def logout():
    """User logout"""
    return {"message": "已登出"}

@router.get("/me")
async def get_me(username: str = Depends(require_auth)):
    """Get current user info"""
    return {"username": username}
