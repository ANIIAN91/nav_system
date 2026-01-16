"""Security utilities"""
import time
import socket
import ipaddress
import uuid
from datetime import datetime, timedelta
from typing import Optional, Tuple
from collections import defaultdict
from urllib.parse import urlparse

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Rate limiting storage
login_attempts = defaultdict(list)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token with jti (JWT ID)"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))

    # 添加 jti（JWT ID）用于撤销
    jti = str(uuid.uuid4())
    to_encode.update({
        "exp": expire,
        "jti": jti,
        "iat": datetime.utcnow()  # 签发时间
    })

    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

async def verify_token(token: str, db: AsyncSession) -> Optional[str]:
    """Verify a JWT token and check blacklist"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        jti: str = payload.get("jti")

        # 检查 token 是否在黑名单中
        if jti:
            # Import here to avoid circular dependency
            from app.models.token_blacklist import TokenBlacklist
            result = await db.execute(
                select(TokenBlacklist).where(TokenBlacklist.jti == jti)
            )
            if result.scalar_one_or_none():
                return None  # Token 已被撤销

        return username
    except JWTError:
        return None

def check_rate_limit(ip: str) -> Tuple[bool, int]:
    """Check login rate limit, returns (allowed, remaining_lockout_seconds)"""
    now = time.time()
    login_attempts[ip] = [t for t in login_attempts[ip] if now - t < settings.lockout_seconds]

    if len(login_attempts[ip]) >= settings.max_login_attempts:
        oldest = min(login_attempts[ip])
        remaining = int(settings.lockout_seconds - (now - oldest))
        if remaining > 0:
            return False, remaining
        login_attempts[ip] = []

    return True, 0

def record_failed_login(ip: str):
    """Record a failed login attempt"""
    login_attempts[ip].append(time.time())

def clear_login_attempts(ip: str):
    """Clear login attempts after successful login"""
    login_attempts[ip] = []

def is_safe_url(url: str) -> Tuple[bool, str]:
    """Validate URL to prevent SSRF attacks"""
    try:
        parsed = urlparse(url)

        if parsed.scheme not in ('http', 'https'):
            return False, f"不支持的协议: {parsed.scheme}，只允许 http/https"

        hostname = parsed.hostname
        if not hostname:
            return False, "无效的 URL：缺少主机名"

        blocked_hostnames = [
            'localhost', '127.0.0.1', '0.0.0.0',
            'metadata.google.internal',
            '169.254.169.254',
            'metadata.azure.com',
        ]
        if hostname.lower() in blocked_hostnames:
            return False, f"禁止访问内部地址: {hostname}"

        try:
            ip_addresses = socket.getaddrinfo(hostname, None)
            for addr_info in ip_addresses:
                ip_str = addr_info[4][0]
                ip = ipaddress.ip_address(ip_str)

                # Allow 198.18.0.0/15 (benchmark testing range, often used by proxies)
                if ip_str.startswith('198.18.') or ip_str.startswith('198.19.'):
                    continue

                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                    return False, f"禁止访问内部/私有 IP 地址: {ip_str}"
        except socket.gaierror:
            pass

        return True, ""
    except Exception as e:
        return False, f"URL 验证失败: {str(e)}"
