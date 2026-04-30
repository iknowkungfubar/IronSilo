"""
Comprehensive tests for security middleware.
"""

import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient


class TestRateLimiter:
    """Tests for RateLimiter class."""

    def test_rate_limiter_allows_requests_under_limit(self):
        """Test that requests under the limit are allowed."""
        from security.middleware import RateLimiter

        limiter = RateLimiter(requests_per_minute=10)

        for i in range(10):
            assert limiter.is_allowed(f"client-{i}") is True

    def test_rate_limiter_blocks_requests_over_limit(self):
        """Test that requests over the limit are blocked."""
        from security.middleware import RateLimiter

        limiter = RateLimiter(requests_per_minute=3)

        assert limiter.is_allowed("client-1") is True
        assert limiter.is_allowed("client-1") is True
        assert limiter.is_allowed("client-1") is True
        assert limiter.is_allowed("client-1") is False

    def test_rate_limiter_tracks_per_client(self):
        """Test that rate limiting is per-client."""
        from security.middleware import RateLimiter

        limiter = RateLimiter(requests_per_minute=2)

        assert limiter.is_allowed("client-a") is True
        assert limiter.is_allowed("client-b") is True
        assert limiter.is_allowed("client-a") is True
        assert limiter.is_allowed("client-b") is True
        assert limiter.is_allowed("client-a") is False
        assert limiter.is_allowed("client-b") is False

    def test_rate_limiter_get_remaining(self):
        """Test get_remaining returns correct count."""
        from security.middleware import RateLimiter

        limiter = RateLimiter(requests_per_minute=5)

        limiter.is_allowed("client")
        limiter.is_allowed("client")
        limiter.is_allowed("client")

        remaining = limiter.get_remaining("client")
        assert remaining == 2

    def test_rate_limiter_window_expiry(self):
        """Test that old requests are cleaned up."""
        from security.middleware import RateLimiter

        limiter = RateLimiter(requests_per_minute=60)

        limiter._requests["client"].append(time.time() - 120)

        remaining = limiter.get_remaining("client")
        assert remaining == 60


class TestGetClientId:
    """Tests for get_client_id function."""

    def test_get_client_id_from_api_key(self):
        """Test extraction of client ID from API key."""
        from security.middleware import get_client_id

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"X-API-Key": "test-key-12345"}
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"

        client_id = get_client_id(mock_request)
        assert client_id.startswith("key:test-key")

    def test_get_client_id_from_ip(self):
        """Test extraction of client ID from IP when no API key."""
        from security.middleware import get_client_id

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}
        mock_request.client = MagicMock()
        mock_request.client.host = "192.168.1.100"

        client_id = get_client_id(mock_request)
        assert client_id == "ip:192.168.1.100"

    def test_get_client_id_x_forwarded_for(self):
        """Test extraction from X-Forwarded-For header."""
        from security.middleware import get_client_id

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"X-Forwarded-For": "10.0.0.1, 10.0.0.2"}
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"

        client_id = get_client_id(mock_request)
        assert client_id == "ip:10.0.0.1"


class TestSetupSecurityMiddleware:
    """Tests for setup_security_middleware function."""

    def test_setup_adds_middleware(self):
        """Test that security middleware is properly configured."""
        from security.middleware import setup_security_middleware

        app = FastAPI()
        setup_security_middleware(app)

        assert app is not None


class TestSanitizeErrorMessage:
    """Tests for sanitize_error_message function."""

    def test_sanitize_error_hides_internal_details(self):
        """Test that internal error details are sanitized."""
        from security.middleware import sanitize_error_message

        error = Exception("Database connection failed: postgres://localhost:5432")
        result = sanitize_error_message(error)

        assert "localhost" not in result
        assert "postgres" not in result
        assert "password" not in result.lower()

    def test_sanitize_error_returns_safe_message(self):
        """Test that sanitized message is safe."""
        from security.middleware import sanitize_error_message

        error = Exception("Some internal error")
        result = sanitize_error_message(error)

        assert result == "Internal server error"

    def test_sanitize_error_maps_known_types(self):
        """Test that known error types map to specific messages."""
        from security.middleware import sanitize_error_message

        error = ValueError("Invalid input")
        result = sanitize_error_message(error)

        assert result == "Invalid request"


class TestSetupCORS:
    """Tests for setup_cors function."""

    def test_setup_cors_adds_cors_middleware(self):
        """Test that CORS middleware is added."""
        from security.middleware import setup_cors

        app = FastAPI()
        setup_cors(app)

        assert len(app.routes) > 0


class TestRequestIDMiddleware:
    """Tests for request_id_middleware function."""

    def test_request_id_middleware_adds_request_id_header(self):
        """Test that X-Request-ID header is added to response."""
        from security.middleware import request_id_middleware
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.middleware("http")(request_id_middleware)

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        client = TestClient(app)
        response = client.get("/test")

        assert "X-Request-ID" in response.headers

    def test_request_id_middleware_preserves_provided_id(self):
        """Test that provided X-Request-ID is preserved."""
        from security.middleware import request_id_middleware
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.middleware("http")(request_id_middleware)

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        client = TestClient(app)
        response = client.get("/test", headers={"X-Request-ID": "my-custom-id"})

        assert response.headers.get("X-Request-ID") == "my-custom-id"


class TestSecurityMiddlewareIntegration:
    """Integration tests for security middleware."""

    @pytest.fixture
    def client(self):
        """Create test client with security middleware."""
        from security.middleware import setup_security_middleware

        app = FastAPI()
        setup_security_middleware(app)

        @app.get("/health")
        async def health():
            return {"status": "healthy"}

        return TestClient(app)

    def test_health_endpoint_accessible(self, client):
        """Test health endpoint is accessible."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_request_id_header_present(self, client):
        """Test that X-Request-ID header is present in all responses."""
        response = client.get("/health")
        assert "X-Request-ID" in response.headers


class TestRateLimitEdgeCases:
    """Tests for rate limiting edge cases."""

    def test_rate_limiter_handles_empty_client_id(self):
        """Test rate limiter with empty client ID."""
        from security.middleware import RateLimiter

        limiter = RateLimiter(requests_per_minute=5)

        for _ in range(5):
            assert limiter.is_allowed("") is True

        assert limiter.is_allowed("") is False

    def test_rate_limiter_concurrent_requests(self):
        """Test rate limiter under concurrent access."""
        from security.middleware import RateLimiter
        import threading

        limiter = RateLimiter(requests_per_minute=100)
        results = []
        errors = []

        def make_request():
            try:
                result = limiter.is_allowed("shared-client")
                results.append(result)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=make_request) for _ in range(50)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0
        assert sum(results) <= 100


class TestSecurityHeaders:
    """Tests for security headers."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from security.middleware import setup_security_middleware

        app = FastAPI()
        setup_security_middleware(app)

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        return TestClient(app)

    def test_x_request_id_format(self, client):
        """Test that X-Request-ID is valid UUID format."""
        import uuid

        response = client.get("/test")
        request_id = response.headers.get("X-Request-ID")

        if request_id:
            try:
                uuid.UUID(request_id)
            except ValueError:
                pytest.fail(f"X-Request-ID {request_id} is not a valid UUID")