"""
Pytest configuration for all tests.
"""

import os

os.environ["RATE_LIMIT_REQUESTS"] = "10000"

import pytest


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset the rate limiter before each test to prevent rate limit issues during testing."""
    try:
        from security.middleware import _rate_limiter
        _rate_limiter._requests.clear()
    except (ImportError, AttributeError):
        pass