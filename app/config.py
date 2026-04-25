"""Application configuration."""

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

VERSION = os.getenv("APP_VERSION", "2.0.0")
GITHUB_URL = "https://github.com/ANIIAN91/nav_system"


def _build_default_database_url(base_dir: Path) -> str:
    """Return the default SQLite URL without touching the filesystem."""
    db_path = base_dir / "data" / "nav_system.db"
    return f"sqlite+aiosqlite:///{db_path}"


@dataclass(slots=True)
class Settings:
    """Application settings resolved from environment variables."""

    base_dir: Path
    data_dir: Path
    articles_dir: Path
    static_dir: Path
    templates_dir: Path
    database_url: str
    secret_key: str
    admin_username: str
    admin_password: str
    admin_password_hash: str
    algorithm: str
    access_token_expire_minutes: int
    max_login_attempts: int
    login_window_seconds: int
    lockout_seconds: int
    max_visit_records: int
    max_update_records: int
    enable_log_cleanup: bool
    log_cleanup_interval_seconds: int

    @classmethod
    def from_env(cls) -> "Settings":
        """Build the settings object from the current process environment."""
        base_dir = Path(__file__).resolve().parent.parent
        return cls(
            base_dir=base_dir,
            data_dir=base_dir / "data",
            articles_dir=base_dir / "articles",
            static_dir=base_dir / "static",
            templates_dir=base_dir / "templates",
            database_url=os.getenv("DATABASE_URL") or _build_default_database_url(base_dir),
            secret_key=os.getenv("SECRET_KEY", ""),
            admin_username=os.getenv("ADMIN_USERNAME", ""),
            admin_password=os.getenv("ADMIN_PASSWORD", ""),
            admin_password_hash=os.getenv("ADMIN_PASSWORD_HASH", ""),
            algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
            access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "43200")),
            max_login_attempts=int(os.getenv("MAX_LOGIN_ATTEMPTS", "5")),
            login_window_seconds=int(os.getenv("LOGIN_WINDOW_SECONDS", "300")),
            lockout_seconds=int(os.getenv("LOCKOUT_SECONDS", "900")),
            max_visit_records=int(os.getenv("MAX_VISIT_RECORDS", "1000")),
            max_update_records=int(os.getenv("MAX_UPDATE_RECORDS", "500")),
            enable_log_cleanup=os.getenv("ENABLE_LOG_CLEANUP", "true").lower() == "true",
            log_cleanup_interval_seconds=int(os.getenv("LOG_CLEANUP_INTERVAL_SECONDS", "21600")),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached settings object."""
    return Settings.from_env()


def reset_settings() -> None:
    """Clear the cached settings object."""
    get_settings.cache_clear()
