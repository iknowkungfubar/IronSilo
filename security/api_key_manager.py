"""
API Key management endpoint for IronSilo.

Provides runtime API key rotation without service restart.
"""

from __future__ import annotations

import hashlib
import os
import secrets
from typing import Any, Dict, Optional

import structlog
from fastapi import APIRouter, HTTPException, status

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/key", tags=["key management"])

_current_api_key_hash: Optional[str] = None


def _is_rotation_enabled() -> bool:
    """Check if key rotation is enabled (reads env var each time)."""
    return os.getenv("KEY_ROTATION_ENABLED", "false").lower() == "true"


def _get_api_key_hash(key: str) -> str:
    """Get SHA256 hash of API key for comparison."""
    return hashlib.sha256(key.encode()).hexdigest()


def _generate_api_key() -> str:
    """Generate a new API key."""
    return secrets.token_urlsafe(32)


def verify_api_key(provided_key: str) -> bool:
    """
    Verify the provided API key against the current key.

    Args:
        provided_key: The API key to verify

    Returns:
        True if key matches, False otherwise
    """
    global _current_api_key_hash

    api_key = os.getenv("IRONSILO_API_KEY", "")

    if not api_key:
        return True

    if _current_api_key_hash is None:
        _current_api_key_hash = _get_api_key_hash(api_key)

    provided_hash = _get_api_key_hash(provided_key)
    return secrets.compare_digest(provided_hash, _current_api_key_hash)


def get_current_key() -> Optional[str]:
    """Get current API key from environment."""
    return os.getenv("IRONSILO_API_KEY", "")


def set_api_key(new_key: str) -> None:
    """
    Set new API key at runtime.

    Args:
        new_key: The new API key to use
    """
    global _current_api_key_hash

    os.environ["IRONSILO_API_KEY"] = new_key
    _current_api_key_hash = _get_api_key_hash(new_key)

    logger.info("api_key_rotated", key_fingerprint=new_key[:8])


def get_key_status() -> Dict[str, Any]:
    """
    Get current API key status.

    Returns key metadata (not the key itself).
    """
    current = get_current_key()

    return {
        "key_configured": bool(current),
        "key_fingerprint": current[:8] if current else None,
        "key_length": len(current) if current else 0,
        "rotation_enabled": _is_rotation_enabled(),
    }


def validate_api_key(key: str) -> Dict[str, bool]:
    """
    Validate an API key without changing state.

    Args:
        key: The API key to validate

    Returns:
        Dictionary with validation result
    """
    is_valid = verify_api_key(key)

    return {"valid": is_valid}


async def rotate_api_key(
    current_key: str,
    new_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Rotate the API key.

    Requires the current key for authentication and generates a new one.

    Args:
        current_key: The current API key for verification
        new_key: Optional new key (generates one if not provided)

    Returns:
        Dictionary with new key info
    """
    if not _is_rotation_enabled():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Key rotation is not enabled. Set KEY_ROTATION_ENABLED=true",
        )

    current = get_current_key()
    if current and current != current_key:
        logger.warning("api_key_rotation_failed", reason="invalid_current_key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid current API key",
        )

    if new_key is None:
        new_key = _generate_api_key()

    if len(new_key) < 16:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key must be at least 16 characters",
        )

    set_api_key(new_key)

    logger.info(
        "api_key_rotated_successfully",
        key_fingerprint=new_key[:8],
        rotated_by="api_endpoint",
    )

    return {
        "message": "API key rotated successfully",
        "new_key": new_key,
        "key_fingerprint": new_key[:8],
        "warning": "Update your clients with the new key immediately",
    }