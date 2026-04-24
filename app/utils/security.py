"""Security utilities."""

import ipaddress
import socket
import uuid
from datetime import datetime, timedelta
from typing import Optional, Tuple
from urllib.parse import urlparse

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token with a JTI."""
    settings = get_settings()
    to_encode = data.copy()
    issued_at = datetime.utcnow()
    expire = issued_at + (expires_delta or timedelta(minutes=15))
    to_encode.update(
        {
            "exp": expire,
            "jti": str(uuid.uuid4()),
            "iat": issued_at,
        }
    )
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> Optional[dict]:
    """Decode a JWT access token payload using the configured app secrets."""
    settings = get_settings()
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None


async def verify_token(token: str, db: AsyncSession) -> Optional[str]:
    """Verify a JWT token through the shared token service boundary."""
    from app.services.auth import TokenService

    return await TokenService().verify_token(token, db)


def is_safe_url(url: str) -> Tuple[bool, str]:
    """Validate URL to prevent SSRF attacks."""
    try:
        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https"):
            return False, f"不支持的协议: {parsed.scheme}，只允许 http/https"

        hostname = parsed.hostname
        if not hostname:
            return False, "无效的 URL：缺少主机名"

        blocked_hostnames = [
            "localhost",
            "127.0.0.1",
            "0.0.0.0",
            "metadata.google.internal",
            "169.254.169.254",
            "metadata.azure.com",
        ]
        if hostname.lower() in blocked_hostnames:
            return False, f"禁止访问内部地址: {hostname}"

        try:
            ip_addresses = socket.getaddrinfo(hostname, None)
            for addr_info in ip_addresses:
                ip_str = addr_info[4][0]
                ip = ipaddress.ip_address(ip_str)
                if ip_str.startswith("198.18.") or ip_str.startswith("198.19."):
                    continue
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                    return False, f"禁止访问内部/私有 IP 地址: {ip_str}"
        except socket.gaierror:
            pass

        return True, ""
    except Exception as exc:
        return False, f"URL 验证失败: {str(exc)}"
