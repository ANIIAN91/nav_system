"""Authentication service boundaries."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models.token_blacklist import TokenBlacklist
from app.services.rate_limit import RateLimiter, get_rate_limiter
from app.utils.security import create_access_token, decode_access_token, get_password_hash, verify_password


@dataclass(frozen=True)
class CredentialConfig:
    """Resolved admin credential configuration."""

    admin_username: str
    password_hash: str | None


def _resolve_password_hash(settings: Settings) -> str | None:
    """Resolve the effective admin password hash once per process."""
    if settings.admin_password_hash and settings.admin_password_hash.startswith("$2"):
        return settings.admin_password_hash
    if settings.admin_password:
        return get_password_hash(settings.admin_password)
    return None


@lru_cache(maxsize=1)
def get_credential_config() -> CredentialConfig:
    """Return the cached admin credential configuration."""
    settings = get_settings()
    return CredentialConfig(
        admin_username=settings.admin_username,
        password_hash=_resolve_password_hash(settings),
    )


def reset_auth_service_state() -> None:
    """Reset cached auth-derived state for tests or explicit refreshes."""
    get_credential_config.cache_clear()


class CredentialService:
    """Handle username/password login validation."""

    def __init__(
        self,
        rate_limiter: RateLimiter | None = None,
        settings: Settings | None = None,
        credential_config: CredentialConfig | None = None,
    ):
        self.settings = settings or get_settings()
        self.rate_limiter = rate_limiter or get_rate_limiter()
        self.credential_config = credential_config or get_credential_config()
        self.password_hash = self.credential_config.password_hash

    def authenticate(self, username: str, password: str, client_ip: str) -> dict:
        """Authenticate user and return a bearer token."""
        allowed, lockout_remaining = self.rate_limiter.check(client_ip)
        if not allowed:
            return {"error": f"登录尝试次数过多，请在 {lockout_remaining} 秒后重试", "status": 429}

        if username != self.credential_config.admin_username:
            self.rate_limiter.record_failure(client_ip)
            return {"error": "用户名或密码错误", "status": 401}

        if not self.password_hash or not verify_password(password, self.password_hash):
            self.rate_limiter.record_failure(client_ip)
            return {"error": "用户名或密码错误", "status": 401}

        self.rate_limiter.clear(client_ip)
        access_token = create_access_token(
            data={"sub": username},
            expires_delta=timedelta(minutes=self.settings.access_token_expire_minutes),
        )
        return {"access_token": access_token, "token_type": "bearer"}

    def validate_config(self) -> list[str]:
        """Validate security configuration for the login boundary."""
        errors: list[str] = []
        if not self.settings.secret_key:
            errors.append("SECRET_KEY 环境变量未设置")
        elif len(self.settings.secret_key) < 16:
            errors.append("SECRET_KEY 太短，建议至少 32 字符")
        if not self.credential_config.admin_username:
            errors.append("ADMIN_USERNAME 环境变量未设置")
        if self.settings.admin_password_hash and self.password_hash is None and not self.settings.admin_password:
            errors.append("ADMIN_PASSWORD_HASH 必须是受支持的 bcrypt hash")
        if not self.password_hash:
            errors.append("需要设置 ADMIN_PASSWORD 或 ADMIN_PASSWORD_HASH")
        return errors


class TokenService:
    """Handle JWT verification, revoke, and blacklist cleanup."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    async def verify_token(self, token: str, db: AsyncSession) -> str | None:
        """Verify a JWT and return the username if the token is valid."""
        payload = decode_access_token(token)
        if payload is None:
            return None

        username = payload.get("sub")
        jti = payload.get("jti")
        if not username:
            return None
        if jti and await self.is_token_revoked(jti, db):
            return None
        return username

    async def revoke_token(self, token: str, db: AsyncSession) -> bool:
        """Revoke a JWT by storing its JTI in the blacklist."""
        payload = decode_access_token(token)
        if payload is None:
            return False

        jti = payload.get("jti")
        username = payload.get("sub")
        exp = payload.get("exp")
        if not jti or not username or not exp:
            return False

        if not await self.is_token_revoked(jti, db):
            db.add(
                TokenBlacklist(
                    jti=jti,
                    username=username,
                    revoked_at=datetime.utcnow(),
                    expires_at=datetime.utcfromtimestamp(exp),
                    reason="logout",
                )
            )
        return True

    async def cleanup_expired_tokens(self, db: AsyncSession) -> int:
        """Delete expired blacklist entries."""
        result = await db.execute(
            delete(TokenBlacklist).where(TokenBlacklist.expires_at < datetime.utcnow())
        )
        return result.rowcount or 0

    async def is_token_revoked(self, jti: str, db: AsyncSession) -> bool:
        """Return whether a token JTI is already blacklisted."""
        result = await db.execute(select(TokenBlacklist).where(TokenBlacklist.jti == jti))
        return result.scalar_one_or_none() is not None


class AuthService:
    """Backward-compatible facade over credential and token services."""

    def __init__(
        self,
        rate_limiter: RateLimiter | None = None,
        settings: Settings | None = None,
        credential_service: CredentialService | None = None,
        token_service: TokenService | None = None,
    ):
        resolved_settings = settings or get_settings()
        self.credential_service = credential_service or CredentialService(
            rate_limiter=rate_limiter,
            settings=resolved_settings,
        )
        self.token_service = token_service or TokenService(settings=resolved_settings)
        self.settings = self.credential_service.settings
        self.rate_limiter = self.credential_service.rate_limiter
        self.password_hash = self.credential_service.password_hash

    def authenticate(self, username: str, password: str, client_ip: str) -> dict:
        return self.credential_service.authenticate(username, password, client_ip)

    async def verify_token(self, token: str, db: AsyncSession) -> str | None:
        return await self.token_service.verify_token(token, db)

    async def revoke_token(self, token: str, db: AsyncSession) -> bool:
        return await self.token_service.revoke_token(token, db)

    async def cleanup_expired_tokens(self, db: AsyncSession) -> int:
        return await self.token_service.cleanup_expired_tokens(db)

    def validate_config(self) -> list[str]:
        return self.credential_service.validate_config()


def get_credential_service() -> CredentialService:
    """Return the login credential boundary."""
    return CredentialService()


def get_token_service() -> TokenService:
    """Return the JWT/token boundary."""
    return TokenService()


def get_auth_service() -> AuthService:
    """Return the backward-compatible authentication facade."""
    return AuthService()
