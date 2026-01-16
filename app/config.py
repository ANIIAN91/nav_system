"""Application configuration"""
import os
from pathlib import Path
from functools import lru_cache
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

# Application version
VERSION = "1.0.0"
GITHUB_URL = "https://github.com/ANIIAN91/nav_system"

def build_database_url() -> str:
    """Build database URL for SQLite"""
    url = os.getenv("DATABASE_URL", "")
    if url:
        return url

    # Default SQLite database in data directory
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "data"
    data_dir.mkdir(exist_ok=True)
    db_path = data_dir / "nav_system.db"
    return f"sqlite+aiosqlite:///{db_path}"

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
        self.access_token_expire_minutes: int = 60  # 60 minutes - Improved security

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
