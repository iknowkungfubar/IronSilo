"""
Comprehensive unit tests for proxy module.

Tests cover:
- Proxy configuration
- Request handling with validation
- Compression logic (mocked)
- Streaming support
- Error handling
- Health check endpoint
"""

import json
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# We need to mock llmlingua before importing proxy
import sys
mock_llmlingua = MagicMock()
sys.modules["llmlingua"] = mock_llmlingua

from proxy.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ErrorResponse,
    HealthResponse,
    Message,
    Role,
)


class TestProxyConfiguration:
    """Test proxy configuration constants."""
    
    def test_llm_endpoint_default(self):
        """Test LLM endpoint has a valid default."""
        import os
        
        default_endpoint = os.getenv("LLM_ENDPOINT", "http://host.docker.internal:8000/v1/chat/completions")
        assert "8000" in default_endpoint or "chat/completions" in default_endpoint
        assert default_endpoint.startswith("http")
    
    def test_compression_threshold_default(self):
        """Test compression threshold has a reasonable default."""
        import os
        threshold = int(os.getenv("COMPRESSION_THRESHOLD", "1000"))
        assert threshold > 0
        assert threshold <= 100000  # Reasonable upper bound
    
    def test_compression_rate_default(self):
        """Test compression rate is between 0 and 1."""
        import os
        rate = float(os.getenv("COMPRESSION_RATE", "0.6"))
        assert 0 < rate <= 1.0


class TestProxyModule:
    """Test proxy module structure and exports."""
    
    def test_proxy_has_app(self):
        """Test that proxy module exports FastAPI app."""
        from proxy.proxy import app
        
        assert app is not None
        assert hasattr(app, "routes")
    
    def test_proxy_has_compress_function(self):
        """Test that proxy module exports compression function."""
        from proxy.proxy import _compress_content
        
        assert callable(_compress_content)
    
    def test_proxy_has_process_messages_function(self):
        """Test that proxy module exports message processing function."""
        from proxy.proxy import _process_messages
        
        assert callable(_process_messages)


class TestCompressionLogic:
    """Test compression logic in isolation."""
    
    def test_compress_short_content(self):
        """Test that short content is not compressed."""
        from proxy.proxy import _compress_content
        
        short_content = "short"
        result = _compress_content(short_content)
        
        # Should return original content unchanged
        assert result == short_content
    
    def test_compress_empty_content(self):
        """Test that empty content is handled."""
        from proxy.proxy import _compress_content
        
        result = _compress_content("")
        assert result == ""
    
    def test_compress_with_llmlingua_mocked(self):
        """Test compression with mocked LLMLingua."""
        from proxy import proxy
        from proxy.proxy import _compress_content
        
        # Mock the compressor
        original_compressor = proxy._compressor
        original_enabled = proxy._compression_enabled
        
        try:
            mock_compressor = MagicMock()
            mock_compressor.compress_prompt.return_value = {
                "compressed_prompt": "compressed text",
            }
            
            proxy._compressor = mock_compressor
            proxy._compression_enabled = True
            
            # Long content should trigger compression
            long_content = "x" * 2000
            result = _compress_content(long_content)
            
            # Verify compression was called
            mock_compressor.compress_prompt.assert_called_once()
            assert result == "compressed text"
            
        finally:
            # Restore original state
            proxy._compressor = original_compressor
            proxy._compression_enabled = original_enabled
    
    def test_compress_handles_exception(self):
        """Test that compression failures are handled gracefully."""
        from proxy import proxy
        from proxy.proxy import _compress_content
        
        original_compressor = proxy._compressor
        original_enabled = proxy._compression_enabled
        
        try:
            mock_compressor = MagicMock()
            mock_compressor.compress_prompt.side_effect = Exception("Compression failed")
            
            proxy._compressor = mock_compressor
            proxy._compression_enabled = True
            
            long_content = "x" * 2000
            result = _compress_content(long_content)
            
            # Should return original content on failure
            assert result == long_content
            
        finally:
            proxy._compressor = original_compressor
            proxy._compression_enabled = original_enabled


class TestProcessMessages:
    """Test message processing logic."""
    
    def test_process_basic_messages(self):
        """Test processing basic messages."""
        from proxy.proxy import _process_messages
        
        messages = [
            Message(role=Role.USER, content="Hello"),
            Message(role=Role.ASSISTANT, content="Hi there!"),
        ]
        
        result = _process_messages(messages)
        
        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "Hello"
        assert result[1]["role"] == "assistant"
    
    def test_process_messages_with_none_content(self):
        """Test processing messages with None content."""
        from proxy.proxy import _process_messages
        
        messages = [
            Message(role=Role.ASSISTANT, content=None),
        ]
        
        result = _process_messages(messages)
        
        assert len(result) == 1
        assert "content" not in result[0] or result[0].get("content") is None
    
    def test_process_messages_excludes_none_values(self):
        """Test that None values are excluded from output."""
        from proxy.proxy import _process_messages
        
        messages = [
            Message(role=Role.USER, content="Test", name=None),
        ]
        
        result = _process_messages(messages)
        
        # name should not be in output since it's None
        assert "name" not in result[0]


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_endpoint_exists(self):
        """Test that health endpoint is registered."""
        from proxy.proxy import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "compression_enabled" in data
        assert "llm_endpoint" in data
        assert "uptime_seconds" in data
    
    def test_health_returns_valid_model(self):
        """Test that health endpoint returns valid HealthResponse."""
        from proxy.proxy import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        response = client.get("/health")
        
        data = response.json()
        health = HealthResponse(**data)
        
        assert health.status in ("healthy", "degraded", "unhealthy")
        assert isinstance(health.uptime_seconds, float)
        assert health.uptime_seconds >= 0


class TestChatCompletionsEndpoint:
    """Test chat completions endpoint."""
    
    def test_endpoint_exists(self):
        """Test that chat completions endpoint is registered."""
        from proxy.proxy import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        # Just verify the route exists (will fail upstream but route is there)
        response = client.post(
            "/api/v1/chat/completions",
            json={"messages": [{"role": "user", "content": "test"}]},
        )
        
        # Should not be 404 (route not found)
        assert response.status_code != 404
    
    def test_invalid_request_returns_422(self):
        """Test that invalid request returns 422."""
        from proxy.proxy import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        # Empty messages should fail validation
        response = client.post(
            "/api/v1/chat/completions",
            json={"messages": []},
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
    
    def test_missing_messages_returns_422(self):
        """Test that missing messages field returns 422."""
        from proxy.proxy import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        response = client.post(
            "/api/v1/chat/completions",
            json={"model": "test"},
        )
        
        assert response.status_code == 422
    
    def test_valid_request_structure(self):
        """Test that valid request structure is accepted."""
        from proxy.proxy import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        request_data = {
            "messages": [
                {"role": "user", "content": "Hello, world!"}
            ],
            "model": "test-model",
            "temperature": 0.7,
            "max_tokens": 100,
            "stream": False,
        }
        
        # This will fail due to no upstream, but shouldn't fail validation
        response = client.post(
            "/api/v1/chat/completions",
            json=request_data,
        )
        
        # Should be 500 (upstream error) not 422 (validation error)
        assert response.status_code in (200, 500)
    
    def test_invalid_role_returns_422(self):
        """Test that invalid role returns 422."""
        from proxy.proxy import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        response = client.post(
            "/api/v1/chat/completions",
            json={
                "messages": [
                    {"role": "invalid_role", "content": "test"}
                ]
            },
        )
        
        assert response.status_code == 422


class TestStreamingResponse:
    """Test streaming response handling."""
    
    def test_stream_parameter_recognized(self):
        """Test that stream parameter is recognized."""
        from proxy.proxy import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        response = client.post(
            "/api/v1/chat/completions",
            json={
                "messages": [{"role": "user", "content": "test"}],
                "stream": True,
            },
        )
        
        # Should not be 422
        assert response.status_code != 422


class TestErrorHandling:
    """Test error handling in proxy."""
    
    def test_error_response_format(self):
        """Test error response format."""
        from proxy.models import ErrorResponse
        
        error = ErrorResponse.create(
            message="Test error",
            type="test_error",
            code="TEST001",
        )
        
        data = error.model_dump()
        assert "error" in data
        assert data["error"]["message"] == "Test error"
        assert data["error"]["type"] == "test_error"
        assert data["error"]["code"] == "TEST001"
    
    def test_error_response_minimal(self):
        """Test minimal error response."""
        from proxy.models import ErrorResponse
        
        error = ErrorResponse.create(message="Simple error")
        
        data = error.model_dump()
        assert data["error"]["message"] == "Simple error"
        assert data["error"]["type"] == "api_error"
        assert "code" not in data["error"]


class TestRequestValidation:
    """Test request validation edge cases."""
    
    def test_temperature_validation(self):
        """Test temperature bounds validation."""
        from proxy.models import ChatCompletionRequest
        
        # Valid temperatures
        for temp in [0.0, 1.0, 2.0]:
            req = ChatCompletionRequest(
                messages=[Message(role=Role.USER, content="test")],
                temperature=temp,
            )
            assert req.temperature == temp
        
        # Invalid temperatures
        for temp in [-0.1, 2.1]:
            with pytest.raises(Exception):
                ChatCompletionRequest(
                    messages=[Message(role=Role.USER, content="test")],
                    temperature=temp,
                )
    
    def test_max_tokens_validation(self):
        """Test max_tokens bounds validation."""
        from proxy.models import ChatCompletionRequest
        
        # Valid
        req = ChatCompletionRequest(
            messages=[Message(role=Role.USER, content="test")],
            max_tokens=100,
        )
        assert req.max_tokens == 100
        
        # Invalid (must be >= 1)
        with pytest.raises(Exception):
            ChatCompletionRequest(
                messages=[Message(role=Role.USER, content="test")],
                max_tokens=0,
            )
    
    def test_messages_cannot_be_empty(self):
        """Test that empty messages list is rejected."""
        from proxy.models import ChatCompletionRequest
        
        with pytest.raises(Exception):
            ChatCompletionRequest(messages=[])
    
    def test_stream_defaults_to_false(self):
        """Test that stream defaults to False."""
        from proxy.models import ChatCompletionRequest
        
        req = ChatCompletionRequest(
            messages=[Message(role=Role.USER, content="test")],
        )
        assert req.stream is False
    
    def test_extra_fields_preserved(self):
        """Test that extra fields are preserved for pass-through."""
        from proxy.models import ChatCompletionRequest
        
        req = ChatCompletionRequest(
            messages=[Message(role=Role.USER, content="test")],
            extra_fields={"custom_param": "value"},
        )
        assert req.extra_fields.get("custom_param") == "value"
