"""
Integration tests for the LLMLingua Proxy.

Tests cover:
- End-to-end request/response flow
- Mock upstream LLM integration
- Streaming responses
- Error handling with real HTTP client
"""

import asyncio
import json
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, Response

# Mock llmlingua before importing proxy
import sys
mock_llmlingua = MagicMock()
sys.modules["llmlingua"] = mock_llmlingua

from proxy.proxy import app, _process_messages, _compress_content
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
    
    def test_chat_completions_validation_flow(self, client):
        """Test complete validation flow for chat completions."""
        # Test valid request structure
        valid_request = {
            "messages": [
                {"role": "user", "content": "Hello, world!"}
            ],
            "model": "test-model",
            "temperature": 0.7,
            "max_tokens": 100,
        }
        
        # This will fail due to no upstream, but should pass validation
        response = client.post(
            "/api/v1/chat/completions",
            json=valid_request,
        )
        
        # Should be 500 (upstream error) not 422 (validation error)
        assert response.status_code in [200, 500]
    
    def test_multiple_messages_integration(self, client):
        """Test request with multiple messages in conversation."""
        request_data = {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is Python?"},
                {"role": "assistant", "content": "Python is a programming language."},
                {"role": "user", "content": "Tell me more about it."},
            ],
            "temperature": 0.5,
        }
        
        response = client.post(
            "/api/v1/chat/completions",
            json=request_data,
        )
        
        # Should not fail validation
        assert response.status_code != 422
    
    def test_streaming_request_integration(self, client):
        """Test streaming request is recognized."""
        request_data = {
            "messages": [
                {"role": "user", "content": "Stream this response"}
            ],
            "stream": True,
        }
        
        response = client.post(
            "/api/v1/chat/completions",
            json=request_data,
        )
        
        # Should not be 422 (validation error)
        assert response.status_code != 422
    
    def test_tool_messages_integration(self, client):
        """Test tool messages are handled."""
        request_data = {
            "messages": [
                {"role": "user", "content": "Calculate 2+2"},
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_123",
                            "type": "function",
                            "function": {
                                "name": "calculator",
                                "arguments": '{"expression": "2+2"}'
                            }
                        }
                    ]
                },
                {
                    "role": "tool",
                    "content": "4",
                    "tool_call_id": "call_123"
                },
            ],
        }
        
        response = client.post(
            "/api/v1/chat/completions",
            json=request_data,
        )
        
        # Should not be 422 (validation error)
        assert response.status_code != 422


class TestProcessMessagesIntegration:
    """Integration tests for message processing."""
    
    def test_process_messages_with_compression(self):
        """Test message processing with mock compression."""
        from proxy import proxy
        
        # Save original state
        original_compressor = proxy._compressor
        original_enabled = proxy._compression_enabled
        
        try:
            # Enable compression with mock
            mock_compressor = MagicMock()
            mock_compressor.compress_prompt.return_value = {
                "compressed_prompt": "compressed content",
            }
            proxy._compressor = mock_compressor
            proxy._compression_enabled = True
            
            # Create long message content
            long_content = "This is a very long message. " * 100  # > 1000 chars
            messages = [
                Message(role=Role.USER, content=long_content),
                Message(role=Role.ASSISTANT, content="Response"),
            ]
            
            result = _process_messages(messages)
            
            # Should have processed both messages
            assert len(result) == 2
            
            # First message should be compressed
            assert result[0]["role"] == "user"
            assert result[0]["content"] == "compressed content"
            
        finally:
            proxy._compressor = original_compressor
            proxy._compression_enabled = original_enabled
    
    def test_process_messages_without_compression(self):
        """Test message processing without compression."""
        from proxy import proxy
        
        # Save original state
        original_compressor = proxy._compressor
        original_enabled = proxy._compression_enabled
        
        try:
            proxy._compression_enabled = False
            
            messages = [
                Message(role=Role.USER, content="Short message"),
                Message(role=Role.ASSISTANT, content="Response"),
            ]
            
            result = _process_messages(messages)
            
            assert len(result) == 2
            assert result[0]["content"] == "Short message"
            assert result[1]["content"] == "Response"
            
        finally:
            proxy._compressor = original_compressor
            proxy._compression_enabled = original_enabled
    
    def test_process_messages_mixed_content(self):
        """Test processing messages with mixed content types."""
        messages = [
            Message(role=Role.SYSTEM, content="System prompt"),
            Message(role=Role.USER, content="User message"),
            Message(role=Role.ASSISTANT, content=None),  # Tool call
            Message(role=Role.TOOL, content="Tool result"),
        ]
        
        result = _process_messages(messages)
        
        assert len(result) == 4
        assert result[0]["role"] == "system"
        assert result[1]["role"] == "user"
        assert result[2]["role"] == "assistant"
        assert result[3]["role"] == "tool"


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
    
    def test_compress_with_compression_disabled(self):
        """Test compression when disabled."""
        from proxy import proxy
        
        original_enabled = proxy._compression_enabled
        
        try:
            proxy._compression_enabled = False
            
            long_content = "x" * 2000
            result = _compress_content(long_content)
            
            assert result == long_content
            
        finally:
            proxy._compression_enabled = original_enabled
    
    def test_compress_with_compressor_error(self):
        """Test compression handles errors gracefully."""
        from proxy import proxy
        
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
                "temperature": 2.5,  # Invalid: > 2.0
            },
        )
        
        assert response.status_code == 422
    
    def test_invalid_max_tokens_zero(self, client):
        """Test error when max_tokens is zero."""
        response = client.post(
            "/api/v1/chat/completions",
            json={
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 0,  # Invalid: must be >= 1
            },
        )
        
        assert response.status_code == 422
