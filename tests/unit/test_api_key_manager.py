"""
Tests for API key management endpoint.
"""

import os
import importlib
from unittest.mock import patch

import pytest


class TestApiKeyManager:
    """Tests for API key management."""

    @pytest.fixture(autouse=True)
    def clean_env(self):
        """Clean environment before each test and reset module state."""
        original = os.environ.copy()
        os.environ.pop("IRONSILO_API_KEY", None)
        os.environ.pop("KEY_ROTATION_ENABLED", None)

        if "security.api_key_manager" in globals():
            importlib.reload(globals()["security.api_key_manager"])

        yield

        os.environ.clear()
        os.environ.update(original)

    @pytest.fixture
    def mock_env(self, clean_env):
        """Set up mock environment."""
        os.environ["IRONSILO_API_KEY"] = "test-api-key-12345"
        os.environ["KEY_ROTATION_ENABLED"] = "false"
        return os.environ

    def test_generate_api_key_length(self):
        """Test that generated API key has sufficient length."""
        from security.api_key_manager import _generate_api_key
        
        key = _generate_api_key()
        assert len(key) >= 16, "API key must be at least 16 characters"

    def test_generate_api_key_uniqueness(self):
        """Test that generated API keys are unique."""
        from security.api_key_manager import _generate_api_key
        
        keys = [_generate_api_key() for _ in range(100)]
        assert len(set(keys)) == 100, "Generated keys should be unique"

    def test_get_api_key_hash(self):
        """Test API key hashing."""
        from security.api_key_manager import _get_api_key_hash
        
        key = "test-key-123"
        hash1 = _get_api_key_hash(key)
        hash2 = _get_api_key_hash(key)
        
        assert hash1 == hash2, "Same key should produce same hash"
        assert len(hash1) == 64, "SHA256 hash should be 64 characters"

    def test_verify_api_key_no_key_configured(self, clean_env):
        """Test verification when no API key is configured."""
        from security.api_key_manager import verify_api_key
        
        result = verify_api_key("any-key")
        assert result is True, "Should allow all keys when no key configured"

    def test_verify_api_key_correct_key(self, mock_env):
        """Test verification with correct API key."""
        from security.api_key_manager import verify_api_key, get_current_key
        
        current_key = get_current_key()
        result = verify_api_key(current_key)
        assert result is True, "Should verify correct key"

    def test_verify_api_key_incorrect_key(self, mock_env):
        """Test verification with incorrect API key."""
        from security.api_key_manager import verify_api_key
        
        result = verify_api_key("wrong-key")
        assert result is False, "Should reject incorrect key"

    def test_get_key_status_no_key(self, clean_env):
        """Test key status when no key is configured."""
        from security.api_key_manager import get_key_status
        
        status = get_key_status()
        assert status["key_configured"] is False
        assert status["key_fingerprint"] is None
        assert status["key_length"] == 0

    def test_get_key_status_with_key(self, mock_env):
        """Test key status when key is configured."""
        from security.api_key_manager import get_key_status
        
        status = get_key_status()
        assert status["key_configured"] is True
        assert status["key_fingerprint"] is not None
        assert status["key_length"] > 0

    def test_get_key_status_rotation_disabled(self, mock_env):
        """Test key status shows rotation disabled."""
        from security.api_key_manager import get_key_status
        
        status = get_key_status()
        assert status["rotation_enabled"] is False

    def test_get_key_status_rotation_enabled(self, clean_env):
        """Test key status shows rotation enabled when env var set."""
        os.environ["KEY_ROTATION_ENABLED"] = "true"
        os.environ["IRONSILO_API_KEY"] = "test-key"
        
        from security.api_key_manager import get_key_status
        
        status = get_key_status()
        assert status["rotation_enabled"] is True

    def test_set_api_key(self, clean_env):
        """Test setting new API key at runtime."""
        from security.api_key_manager import set_api_key, get_current_key
        
        new_key = "my-new-test-key"
        set_api_key(new_key)
        
        current = get_current_key()
        assert current == new_key, "API key should be updated"

    def test_set_api_key_updates_hash(self, mock_env):
        """Test that setting new key updates internal hash."""
        from security.api_key_manager import set_api_key, verify_api_key
        
        new_key = "completely-different-key"
        set_api_key(new_key)
        
        result = verify_api_key(new_key)
        assert result is True, "New key should be verifiable immediately"

    def test_validate_api_key_valid(self, mock_env):
        """Test validation endpoint with valid key."""
        import security.api_key_manager as akm
        akm._current_api_key_hash = None

        current_key = akm.get_current_key()
        result = akm.validate_api_key(current_key)
        assert result["valid"] is True

    def test_validate_api_key_invalid(self, mock_env):
        """Test validation endpoint with invalid key."""
        from security.api_key_manager import validate_api_key
        
        result = validate_api_key("invalid-key")
        assert result["valid"] is False


class TestRotateApiKey:
    """Tests for API key rotation endpoint."""

    @pytest.fixture(autouse=True)
    def clean_env(self):
        """Clean environment before each test and reset module state."""
        original = os.environ.copy()
        os.environ.pop("IRONSILO_API_KEY", None)
        os.environ.pop("KEY_ROTATION_ENABLED", None)

        if "security.api_key_manager" in globals():
            importlib.reload(globals()["security.api_key_manager"])

        yield

        os.environ.clear()
        os.environ.update(original)

    @pytest.fixture
    def rotation_enabled_env(self, clean_env):
        """Set up environment with rotation enabled."""
        os.environ["IRONSILO_API_KEY"] = "old-api-key"
        os.environ["KEY_ROTATION_ENABLED"] = "true"
        return os.environ

    @pytest.mark.asyncio
    async def test_rotate_key_not_enabled(self, clean_env):
        """Test that rotation fails when not enabled."""
        from security.api_key_manager import rotate_api_key
        
        with pytest.raises(Exception) as exc_info:
            await rotate_api_key(current_key="any-key")
        
        assert "not enabled" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_rotate_key_invalid_current_key(self, rotation_enabled_env):
        """Test rotation fails with invalid current key."""
        from security.api_key_manager import rotate_api_key
        
        with pytest.raises(Exception) as exc_info:
            await rotate_api_key(current_key="wrong-key")
        
        assert "401" in str(exc_info.value) or "unauthorized" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_rotate_key_success(self, rotation_enabled_env):
        """Test successful key rotation."""
        from security.api_key_manager import rotate_api_key, get_current_key
        
        result = await rotate_api_key(current_key="old-api-key")
        
        assert "new_key" in result
        assert result["new_key"] != "old-api-key"
        assert len(result["new_key"]) >= 16

    @pytest.mark.asyncio
    async def test_rotate_key_with_custom_key(self, rotation_enabled_env):
        """Test rotation with provided custom key."""
        from security.api_key_manager import rotate_api_key
        
        result = await rotate_api_key(
            current_key="old-api-key",
            new_key="my-custom-new-key-12345",
        )
        
        assert result["new_key"] == "my-custom-new-key-12345"

    @pytest.mark.asyncio
    async def test_rotate_key_too_short(self, rotation_enabled_env):
        """Test rotation rejects keys that are too short."""
        from security.api_key_manager import rotate_api_key
        
        with pytest.raises(Exception) as exc_info:
            await rotate_api_key(
                current_key="old-api-key",
                new_key="short",
            )
        
        assert "16" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_rotate_key_no_current_key_configured(self, clean_env):
        """Test rotation when no current key is configured."""
        os.environ["KEY_ROTATION_ENABLED"] = "true"
        
        from security.api_key_manager import rotate_api_key
        
        result = await rotate_api_key(current_key="")
        
        assert "new_key" in result