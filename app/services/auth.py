"""Authentication service"""
from datetime import timedelta
from typing import Optional

from passlib.context import CryptContext

from app.config import get_settings
from app.utils.security import (
    create_access_token, verify_password, get_password_hash,
    check_rate_limit, record_failed_login, clear_login_attempts
)

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    """Authentication service"""

    def __init__(self):
        self.settings = get_settings()
        self._init_password_hash()

    def _init_password_hash(self):
        """Initialize password hash from config"""
        if self.settings.admin_password_hash and self.settings.admin_password_hash.startswith("$2"):
            self.password_hash = self.settings.admin_password_hash
        elif self.settings.admin_password:
            self.password_hash = get_password_hash(self.settings.admin_password)
        else:
            self.password_hash = None

    def authenticate(self, username: str, password: str, client_ip: str) -> dict:
        """Authenticate user and return token"""
        # Check rate limit
        allowed, lockout_remaining = check_rate_limit(client_ip)
        if not allowed:
            return {"error": f"登录尝试次数过多，请在 {lockout_remaining} 秒后重试", "status": 429}

        # Verify username
        if username != self.settings.admin_username:
            record_failed_login(client_ip)
            return {"error": "用户名或密码错误", "status": 401}

        # Verify password
        if not self.password_hash or not verify_password(password, self.password_hash):
            record_failed_login(client_ip)
            return {"error": "用户名或密码错误", "status": 401}

        # Success
        clear_login_attempts(client_ip)
        access_token = create_access_token(
            data={"sub": username},
            expires_delta=timedelta(minutes=self.settings.access_token_expire_minutes)
        )
        return {"access_token": access_token, "token_type": "bearer"}

    def validate_config(self) -> list:
        """Validate security configuration"""
        errors = []
        if not self.settings.secret_key:
            errors.append("SECRET_KEY 环境变量未设置")
        elif len(self.settings.secret_key) < 16:
            errors.append("SECRET_KEY 太短，建议至少 32 字符")
        if not self.settings.admin_username:
            errors.append("ADMIN_USERNAME 环境变量未设置")
        if not self.password_hash:
            errors.append("需要设置 ADMIN_PASSWORD 或 ADMIN_PASSWORD_HASH")
        return errors
