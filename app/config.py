"""Application configuration"""
import os
from pathlib import Path
from functools import lru_cache
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

def build_database_url() -> str:
    """Build database URL with properly encoded password"""
    url = os.getenv("DATABASE_URL", "")
    if url:
        return url

    # Build from individual components if DATABASE_URL not set
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "password")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "postgres")

    # URL encode password to handle special characters like @, !, #, etc.
    encoded_password = quote_plus(db_password)
    return f"postgresql+asyncpg://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"

class Settings:
    """Application settings loaded from environment variables"""

    def __init__(self):
        # Database
        self.database_url: str = build_database_url()

        # Security
        self.secret_key: str = os.getenv("SECRET_KEY", "")
        self.admin_username: str = os.getenv("ADMIN_USERNAME", "")
        self.admin_password: str = os.getenv("ADMIN_PASSWORD", "")
        self.admin_password_hash: str = os.getenv("ADMIN_PASSWORD_HASH", "")
        self.algorithm: str = "HS256"
        self.access_token_expire_minutes: int = 60 * 24  # 24 hours

        # Rate limiting
        self.max_login_attempts: int = 5
        self.login_window_seconds: int = 300
        self.lockout_seconds: int = 900

        # Paths
        self.base_dir: Path = Path(__file__).parent.parent
        self.data_dir: Path = self.base_dir / "data"
        self.articles_dir: Path = self.base_dir / "articles"
        self.static_dir: Path = self.base_dir / "static"
        self.templates_dir: Path = self.base_dir / "templates"

        # Logs
        self.max_visit_records: int = 1000
        self.max_update_records: int = 500

@lru_cache
def get_settings() -> Settings:
    return Settings()
