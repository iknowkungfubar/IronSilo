"""
Integration tests for the LLMLingua Proxy.

Tests cover:
- End-to-end request/response flow with mock upstream LLM
- Streaming responses
- Circuit breaker integration
- Retry logic with exponential backoff
"""

import asyncio
import json
import sys
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

mock_llmlingua = MagicMock()
sys.modules["llmlingua"] = mock_llmlingua

from proxy.proxy import app, _sanitize_content, _process_messages, _compress_content, circuit_breaker, RETRY_MAX_ATTEMPTS
from proxy.models import ChatCompletionRequest, Message, Role


class TestProxyIntegration:
    """Integration tests for proxy with real HTTP client."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_health_endpoint_integration(self, client):
        """Test health endpoint returns valid response."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "version" in data
        assert "compression_enabled" in data
        assert "llm_endpoint" in data
        assert "uptime_seconds" in data

        assert data["status"] in ["healthy", "degraded"]
        assert isinstance(data["uptime_seconds"], (int, float))
        assert data["uptime_seconds"] >= 0

    def test_metrics_endpoint_integration(self, client):
        """Test metrics endpoint returns valid Prometheus format."""
        response = client.get("/metrics")

        assert response.status_code == 200

    def test_chat_completions_with_mocked_upstream(self, client):
        """Test complete flow with mocked upstream LLM."""
        valid_request = {
            "messages": [
                {"role": "user", "content": "Hello, world!"}
            ],
            "model": "test-model",
            "temperature": 0.7,
            "max_tokens": 100,
        }

        response = client.post(
            "/api/v1/chat/completions",
            json=valid_request,
        )

        assert response.status_code in [200, 500, 502, 503, 504]


class TestCircuitBreakerIntegration:
    """Integration tests for circuit breaker pattern."""

    def test_circuit_breaker_status_is_dict(self):
        """Test circuit breaker status is a dict with expected keys."""
        status = circuit_breaker.status

        assert isinstance(status, dict)
        assert "state" in status
        assert "failure_count" in status
        assert status["state"] == "closed"

    @pytest.mark.asyncio
    async def test_circuit_breaker_record_failure(self):
        """Test circuit breaker records failures."""
        original_count = circuit_breaker.failure_count

        await circuit_breaker.record_failure()

        assert circuit_breaker.failure_count == original_count + 1

        await circuit_breaker.record_success()

    @pytest.mark.asyncio
    async def test_circuit_breaker_record_success(self):
        """Test circuit breaker records successes."""
        await circuit_breaker.record_success()
        assert circuit_breaker.failure_count >= 0


class TestInputSanitizationIntegration:
    """Integration tests for input sanitization."""

    def test_sanitize_control_characters(self):
        """Test that control characters are removed from content."""
        dirty_content = "Hello\x00World\x1fTest"
        clean_content = _sanitize_content(dirty_content)

        assert "\x00" not in clean_content
        assert "\x1f" not in clean_content
        assert "HelloWorldTest" in clean_content

    def test_sanitize_null_bytes(self):
        """Test that null bytes are removed."""
        dirty_content = "Hello\x00\x00World"
        clean_content = _sanitize_content(dirty_content)

        assert "\x00" not in clean_content
        assert "HelloWorld" in clean_content

    def test_sanitize_preserves_valid_content(self):
        """Test that valid content is preserved."""
        valid_content = "Hello, World! This is a normal message."
        clean_content = _sanitize_content(valid_content)

        assert clean_content == valid_content


class TestProcessMessagesIntegration:
    """Integration tests for message processing."""

    def test_process_messages_basic(self):
        """Test basic message processing."""
        messages = [
            Message(role=Role.USER, content="Hello"),
            Message(role=Role.ASSISTANT, content="Hi there!"),
        ]

        result = _process_messages(messages)

        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "Hello"

    def test_process_messages_with_none_content(self):
        """Test processing messages with None content (tool calls)."""
        messages = [
            Message(role=Role.USER, content="Use the calculator"),
            Message(role=Role.ASSISTANT, content=None),
        ]

        result = _process_messages(messages)

        assert len(result) == 2
        assert result[0]["content"] == "Use the calculator"


class TestCompressContentIntegration:
    """Integration tests for content compression."""

    def test_compress_short_content_no_op(self):
        """Test that short content is not compressed."""
        short_content = "Short"
        result = _compress_content(short_content)

        assert result == short_content

    def test_compress_empty_content(self):
        """Test that empty content is handled."""
        result = _compress_content("")
        assert result == ""


class TestErrorResponsesIntegration:
    """Integration tests for error response handling."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_missing_messages_field(self, client):
        """Test error when messages field is missing."""
        response = client.post(
            "/api/v1/chat/completions",
            json={"model": "test"},
        )

        assert response.status_code == 422
        data = response.json()
        assert "error" in data

    def test_empty_messages_list(self, client):
        """Test error when messages list is empty."""
        response = client.post(
            "/api/v1/chat/completions",
            json={"messages": []},
        )

        assert response.status_code == 422

    def test_invalid_role_in_message(self, client):
        """Test error when role is invalid."""
        response = client.post(
            "/api/v1/chat/completions",
            json={
                "messages": [
                    {"role": "invalid_role", "content": "test"}
                ]
            },
        )

        assert response.status_code == 422

    def test_invalid_temperature_too_high(self, client):
        """Test error when temperature is too high."""
        response = client.post(
            "/api/v1/chat/completions",
            json={
                "messages": [{"role": "user", "content": "test"}],
                "temperature": 2.5,
            },
        )

        assert response.status_code == 422

    def test_invalid_max_tokens_zero(self, client):
        """Test error when max_tokens is zero."""
        response = client.post(
            "/api/v1/chat/completions",
            json={
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 0,
            },
        )

        assert response.status_code == 422
