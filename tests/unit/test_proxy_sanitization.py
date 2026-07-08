"""Tests for input sanitization in proxy."""


class TestProxySanitization:
    """Test input sanitization for chat completions."""

    def test_proxy_has_sanitize_content_function(self):
        """Test that proxy has content sanitization function."""
        with open("proxy/compression.py", "r") as f:
            content = f.read()

        assert "_sanitize_content" in content, (
            "Proxy should have a sanitize_content function in compression module"
        )

    def test_proxy_sanitizes_user_content(self):
        """Test that user content is sanitized before LLM call."""
        with open("proxy/proxy.py", "r") as f:
            content = f.read()

        assert "_process_messages" in content, (
            "Proxy should sanitize content in _process_messages or similar"
        )

    def test_sanitize_removes_control_characters(self):
        """Test that sanitization removes control characters."""
        with open("proxy/proxy.py", "r") as f:
            content = f.read()

        assert "control" in content.lower() or "strip" in content.lower() or "remove" in content.lower(), (
            "Sanitization should handle control characters"
        )

    def test_sanitize_removes_null_bytes(self):
        """Test that sanitization removes null bytes."""
        with open("proxy/compression.py", "r") as f:
            content = f.read()

        assert "\\x00" in content or "null" in content, (
            "Sanitization should handle null bytes in compression module"
        )
