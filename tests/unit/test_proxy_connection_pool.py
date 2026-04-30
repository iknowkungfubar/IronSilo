"""
Tests for proxy connection pooling.
"""

import pytest
from starlette.testclient import TestClient


class TestProxyConnectionPooling:
    """Tests for proxy HTTP client connection pooling."""

    def test_shared_client_initialized_on_startup(self):
        """Test that shared HTTP client is created on app startup."""
        from proxy.proxy import app

        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200
            assert hasattr(app.state, 'http_client'), "App should have http_client in state"

    def test_http_client_configuration_logged(self):
        """Test that HTTP client is configured with expected settings."""
        from proxy.proxy import HTTP_CLIENT_MAX_CONNECTIONS, HTTP_CLIENT_MAX_KEEPALIVE, HTTP_CLIENT_TIMEOUT

        assert HTTP_CLIENT_MAX_CONNECTIONS == 100
        assert HTTP_CLIENT_MAX_KEEPALIVE == 20
        assert HTTP_CLIENT_TIMEOUT == 60.0

    def test_http_client_is_async(self):
        """Test that HTTP client is async."""
        from proxy.proxy import app
        import httpx

        with TestClient(app):
            client = app.state.http_client
            assert isinstance(client, httpx.AsyncClient), "Client should be AsyncClient"

    def test_http_client_timeout_configured(self):
        """Test that HTTP client has appropriate timeout."""
        from proxy.proxy import app

        with TestClient(app):
            client = app.state.http_client
            assert client.timeout is not None, "Client should have timeout configured"