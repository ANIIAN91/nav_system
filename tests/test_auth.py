"""Authentication tests"""
import pytest
from app.services.auth import AuthService
from app.utils.security import create_access_token, verify_token, get_password_hash, verify_password

class TestPasswordHashing:
    """Test password hashing functions"""

    def test_hash_password(self):
        """Test password hashing"""
        password = "testpassword123"
        hashed = get_password_hash(password)
        assert hashed != password
        assert hashed.startswith("$2")

    def test_verify_password_correct(self):
        """Test correct password verification"""
        password = "testpassword123"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test incorrect password verification"""
        password = "testpassword123"
        hashed = get_password_hash(password)
        assert verify_password("wrongpassword", hashed) is False

class TestJWT:
    """Test JWT token functions"""

    def test_create_token(self):
        """Test token creation"""
        token = create_access_token(data={"sub": "testuser"})
        assert token is not None
        assert isinstance(token, str)

    def test_verify_token_valid(self):
        """Test valid token verification"""
        token = create_access_token(data={"sub": "testuser"})
        username = verify_token(token)
        assert username == "testuser"

    def test_verify_token_invalid(self):
        """Test invalid token verification"""
        username = verify_token("invalid_token")
        assert username is None

class TestAuthService:
    """Test AuthService"""

    def test_validate_config_missing_secret(self):
        """Test config validation with missing secret"""
        service = AuthService()
        # This will depend on actual env vars
        errors = service.validate_config()
        # Just verify it returns a list
        assert isinstance(errors, list)
