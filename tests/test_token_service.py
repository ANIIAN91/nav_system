"""Token service tests."""

from datetime import datetime, timedelta

import pytest

from app.models.token_blacklist import TokenBlacklist
from app.services.auth import TokenService
from app.utils.security import create_access_token


@pytest.mark.asyncio
async def test_token_service_verifies_valid_token(test_db):
    service = TokenService()
    token = create_access_token(data={"sub": "testuser"})

    username = await service.verify_token(token, test_db)

    assert username == "testuser"


@pytest.mark.asyncio
async def test_token_service_rejects_invalid_token(test_db):
    service = TokenService()

    username = await service.verify_token("invalid_token", test_db)

    assert username is None


@pytest.mark.asyncio
async def test_token_service_revoked_token_is_no_longer_valid(test_db):
    service = TokenService()
    token = create_access_token(data={"sub": "testuser"})

    assert await service.verify_token(token, test_db) == "testuser"
    assert await service.revoke_token(token, test_db) is True
    await test_db.commit()

    assert await service.verify_token(token, test_db) is None


@pytest.mark.asyncio
async def test_token_service_cleanup_expired_tokens(test_db):
    service = TokenService()
    test_db.add(
        TokenBlacklist(
            jti="expired-jti",
            username="admin",
            revoked_at=datetime.utcnow() - timedelta(days=1),
            expires_at=datetime.utcnow() - timedelta(minutes=1),
            reason="logout",
        )
    )
    await test_db.commit()

    deleted_count = await service.cleanup_expired_tokens(test_db)
    await test_db.commit()

    assert deleted_count == 1
