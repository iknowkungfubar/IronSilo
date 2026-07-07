"""Tests for proxy/compression.py — prompt compression engine."""

from __future__ import annotations

from proxy.compression import (
    _compress_content,
    _sanitize_content,
    process_messages,
)


class TestSanitizeContent:
    """Tests for _sanitize_content."""

    def test_removes_null_bytes(self):
        """Null bytes should be removed from content."""
        assert _sanitize_content("hello\x00world") == "helloworld"

    def test_strips_whitespace(self):
        """Whitespace should be stripped from content."""
        assert _sanitize_content("  hello  ") == "hello"

    def test_empty_string(self):
        """Empty string should remain empty."""
        assert _sanitize_content("") == ""


class TestCompressContent:
    """Tests for _compress_content."""

    def test_returns_original_when_not_enabled(self):
        """Content should pass through when compression is not enabled."""
        result = _compress_content("hello world")
        assert result == "hello world"

    def test_returns_original_when_content_empty(self):
        """Empty content should pass through even when enabled."""
        result = _compress_content("", enabled=True)
        assert result == ""

    def test_returns_original_when_no_compressor(self, mocker):
        """Content should pass through when no compressor is available."""
        import proxy.compression as comp_mod
        mocker.patch.object(comp_mod, "_get_compressor", return_value=None)
        result = _compress_content("hello world", compressor=None, enabled=True)
        assert result == "hello world"

    def test_with_mock_compressor(self):
        """Compression should work with a mock compressor."""
        class MockCompressor:
            def compress(self, content, target_token=512):
                return {"compressed_prompt": content[:10]}

        result = _compress_content(
            "hello world this is a long message",
            compressor=MockCompressor(),
            enabled=True,
        )
        assert result == "hello worl"

    def test_with_mock_compressor_string_result(self):
        """Compression should handle a string (not dict) result."""
        class MockCompressor:
            def compress(self, content, target_token=512):
                return content[:5]

        result = _compress_content(
            "hello world",
            compressor=MockCompressor(),
            enabled=True,
        )
        assert result == "hello"


class TestProcessMessages:
    """Tests for process_messages."""

    def test_empty_messages(self):
        """Empty message list should return empty list."""
        result = process_messages([])
        assert result == []

    def test_short_user_message_pass_through(self):
        """Short user messages should pass through without compression."""
        messages = [{"role": "user", "content": "short"}]
        result = process_messages(messages, compress_enabled=True, min_compress_chars=1000)
        assert len(result) == 1
        assert result[0]["content"] == "short"

    def test_system_message_pass_through(self):
        """System messages should pass through even when long."""
        long_content = "x" * 2000
        messages = [{"role": "system", "content": long_content}]
        result = process_messages(
            messages, compress_enabled=True, min_compress_chars=100
        )
        assert len(result) == 1
        assert result[0]["content"] == long_content

    def test_user_message_compression(self):
        """Long user messages should be compressed when enabled."""
        class MockCompressor:
            def compress(self, content, target_token=512):
                return {"compressed_prompt": content[:10]}

        long_content = "x" * 2000
        messages = [{"role": "user", "content": long_content}]
        result = process_messages(
            messages,
            compressor=MockCompressor(),
            compress_enabled=True,
            min_compress_chars=100,
        )
        assert len(result) == 1
        assert result[0]["content"] == "x" * 10

    def test_message_with_role_as_enum(self):
        """Messages with role having a .value attribute should be handled."""
        class RoleEnum:
            def __init__(self, value):
                self.value = value

        messages = [{"role": RoleEnum("user"), "content": "hello"}]
        result = process_messages(messages)
        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "hello"

    def test_pydantic_message_object(self):
        """Messages with model_dump should be handled (Pydantic-like)."""
        class MockPydanticMessage:
            def model_dump(self, exclude_none=True):
                return {"role": "user", "content": "hello from pydantic"}

        messages = [MockPydanticMessage()]
        result = process_messages(messages)
        assert len(result) == 1
        assert result[0]["content"] == "hello from pydantic"

    def test_non_dict_message(self):
        """Messages that are neither dict nor Pydantic should fall back to str()."""
        class CustomMessage:
            role = "assistant"
            def __str__(self):
                return "custom response"

        messages = [CustomMessage()]
        result = process_messages(messages)
        assert len(result) == 1
        assert result[0]["role"] == "assistant"

    def test_message_with_none_content(self):
        """Messages with None content should still produce a role entry."""
        messages = [{"role": "user", "content": None}]
        result = process_messages(messages)
        assert len(result) == 1
        assert "role" in result[0]
        assert "content" not in result[0]

    def test_sanitize_before_compress(self):
        """Content should be sanitized before compression."""
        class MockCompressor:
            def compress(self, content, target_token=512):
                return {"compressed_prompt": content}

        messages = [{"role": "user", "content": "  hello\x00world  "}]
        result = process_messages(
            messages,
            compressor=MockCompressor(),
            compress_enabled=True,
            min_compress_chars=1,
        )
        assert result[0]["content"] == "helloworld"
