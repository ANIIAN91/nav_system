"""Authentication tests."""

import pytest

from app.config import get_settings
from app.services.auth import AuthService, CredentialService, reset_auth_service_state
from app.services.rate_limit import reset_rate_limiter, set_rate_limiter
from app.utils.security import create_access_token, get_password_hash, verify_password, verify_token


class TestPasswordHashing:
    """Test password hashing functions."""

    def test_hash_password(self):
        password = "testpassword123"
        hashed = get_password_hash(password)
        assert hashed != password
        assert hashed.startswith("$2")

    def test_verify_password_correct(self):
        password = "testpassword123"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        password = "testpassword123"
        hashed = get_password_hash(password)
        assert verify_password("wrongpassword", hashed) is False


class TestJWT:
    """Test JWT token functions."""

    def test_create_token(self):
        token = create_access_token(data={"sub": "testuser"})
        assert isinstance(token, str)

    @pytest.mark.asyncio
    async def test_verify_token_valid(self, test_db):
        token = create_access_token(data={"sub": "testuser"})
        username = await verify_token(token, test_db)
        assert username == "testuser"

    @pytest.mark.asyncio
    async def test_verify_token_invalid(self, test_db):
        username = await verify_token("invalid_token", test_db)
        assert username is None


@pytest.mark.asyncio
async def test_logout_revokes_token(client, auth_headers):
    """Logout should revoke the current token."""
    response = await client.post("/api/v1/auth/logout", headers=auth_headers)
    assert response.status_code == 200

    me_response = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert me_response.status_code == 401


@pytest.mark.asyncio
async def test_logout_invalid_token_returns_401(client):
    """Invalid tokens should not report a successful server-side logout."""
    response = await client.post("/api/v1/auth/logout", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_rate_limit_response_uses_service_boundary(client, monkeypatch):
    """Route-level login should honor the rate limiter abstraction."""

    class RejectingRateLimiter:
        def check(self, key):
            return False, 42

        def record_failure(self, key):
            return None

        def clear(self, key):
            return None

    monkeypatch.setattr("app.services.auth.get_rate_limiter", lambda: RejectingRateLimiter())

    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert response.status_code == 429
    assert "42" in response.json()["detail"]


def test_auth_service_supports_swappable_rate_limiter_backend():
    """Auth service should work with a replaced rate-limit backend."""

    class RejectingRateLimiter:
        def check(self, key):
            return False, 9

        def record_failure(self, key):
            return None

        def clear(self, key):
            return None

    set_rate_limiter(RejectingRateLimiter())
    try:
        result = AuthService().authenticate("admin", "admin123", "127.0.0.1")
        assert result["status"] == 429
        assert "9" in result["error"]
    finally:
        reset_rate_limiter()


def test_credential_service_supports_admin_password_hash(monkeypatch):
    """Credential service should authenticate against ADMIN_PASSWORD_HASH."""
    settings = get_settings()
    monkeypatch.setattr(settings, "admin_password", "")
    monkeypatch.setattr(settings, "admin_password_hash", get_password_hash("hashed-secret"))
    reset_auth_service_state()

    result = CredentialService().authenticate("admin", "hashed-secret", "127.0.0.1")

    assert result["token_type"] == "bearer"


def test_credential_service_hashes_plain_password_once(monkeypatch):
    """Plain ADMIN_PASSWORD should be hashed once and then reused."""
    settings = get_settings()
    monkeypatch.setattr(settings, "admin_password", "cached-secret")
    monkeypatch.setattr(settings, "admin_password_hash", "")
    reset_auth_service_state()

    original_get_password_hash = get_password_hash
    calls = {"count": 0}

    def counting_get_password_hash(password: str) -> str:
        calls["count"] += 1
        return original_get_password_hash(password)

    monkeypatch.setattr("app.services.auth.get_password_hash", counting_get_password_hash)

    service_a = CredentialService()
    service_b = CredentialService()

    assert service_a.password_hash == service_b.password_hash
    assert calls["count"] == 1


class TestAuthService:
    """Test AuthService."""

    def test_validate_config_returns_list(self):
        errors = AuthService().validate_config()
        assert isinstance(errors, list)
