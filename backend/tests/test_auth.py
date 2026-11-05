import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
from datetime import datetime, timedelta
from jose import jwt, JWTError
from app.config import settings
import bcrypt


def _make_test_token(user_id: int, username: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=1)
    payload = {"sub": str(user_id), "username": username, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


class TestAuth:
    """单元测试：用户认证核心逻辑"""

    def test_password_hashing(self):
        """测试密码哈希与验证"""
        from app.routers.auth import get_password_hash, verify_password
        password = "test_password_123"
        hashed = get_password_hash(password)
        assert hashed != password
        assert verify_password(password, hashed) is True

    def test_password_wrong(self):
        from app.routers.auth import get_password_hash, verify_password
        hashed = get_password_hash("correct_pass")
        assert verify_password("wrong_pass", hashed) is False

    def test_token_creation(self):
        """测试JWT Token创建"""
        from app.routers.auth import create_token
        token = create_token(user_id=42, username="testuser")
        assert token is not None
        assert isinstance(token, str)
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        assert payload["sub"] == "42"
        assert payload["username"] == "testuser"

    def test_token_expiration(self):
        """测试Token过期时间"""
        from app.routers.auth import create_token
        token = create_token(user_id=1, username="user")
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        assert "exp" in payload

    def test_token_decode_with_invalid_secret(self):
        token = _make_test_token(1, "testuser")
        with pytest.raises(JWTError):
            jwt.decode(token, "wrong-secret", algorithms=[settings.jwt_algorithm])

    def test_token_decode_tampered(self):
        token = _make_test_token(1, "testuser")
        tampered = token + "x"
        with pytest.raises(JWTError):
            jwt.decode(tampered, settings.jwt_secret, algorithms=[settings.jwt_algorithm])

    def test_get_current_user_valid_token(self):
        """测试从Token提取用户ID"""
        from app.utils.auth import get_current_user
        import pytest as _pt
        token = _make_test_token(99, "testuser")
        # Simulate FastAPI dependency injection
        user_id = _run_get_current_user_sync(token)
        assert user_id == 99

    def test_get_current_user_missing_auth(self):
        from app.utils.auth import get_current_user
        import asyncio
        with pytest.raises(Exception):
            asyncio.run(get_current_user(authorization=None))

    def test_get_current_user_invalid_prefix(self):
        from app.utils.auth import get_current_user
        import asyncio
        with pytest.raises(Exception):
            asyncio.run(get_current_user(authorization="Invalid token"))


def _run_get_current_user_sync(token):
    """Helper: run async get_current_user synchronously"""
    from app.utils.auth import get_current_user
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(get_current_user(authorization=f"Bearer {token}"))
