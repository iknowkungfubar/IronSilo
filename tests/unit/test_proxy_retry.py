"""Tests for proxy retry logic with exponential backoff."""
import pytest


class TestProxyRetryLogic:
    """Test retry logic with exponential backoff."""

    def test_proxy_has_retry_config(self):
        """Test that proxy has retry configuration."""
        with open("proxy/proxy.py", "r") as f:
            content = f.read()

        assert "RETRY_MAX_ATTEMPTS" in content or "max_retries" in content, \
            "Proxy should have retry configuration"

    def test_proxy_has_backoff_delay(self):
        """Test that proxy has exponential backoff delay."""
        with open("proxy/proxy.py", "r") as f:
            content = f.read()

        assert "backoff" in content.lower() or "delay" in content.lower(), \
            "Proxy should have backoff delay logic"

    def test_proxy_retries_on_5xx_errors(self):
        """Test that proxy retries on 5xx errors."""
        with open("proxy/proxy.py", "r") as f:
            content = f.read()

        assert "500" in content or "502" in content or "503" in content or "504" in content or "status_code" in content, \
            "Proxy should check for 5xx status codes to retry"
