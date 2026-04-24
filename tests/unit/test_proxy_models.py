"""
Unit tests for proxy/models.py module.

Tests cover:
- Pydantic model validation
- Request/response serialization
- Edge cases and error handling
"""

import pytest
from pydantic import ValidationError

from proxy.models import (
    ChatCompletionChunk,
    ChatCompletionRequest,
    ChatCompletionResponse,
    Choice,
    DeltaMessage,
    ErrorResponse,
    HealthResponse,
    Message,
    Role,
    StreamingChoice,
    UsageInfo,
)


class TestRole:
    """Test Role enum."""
    
    def test_role_values(self):
        """Test role enum has expected values."""
        assert Role.SYSTEM == "system"
        assert Role.USER == "user"
        assert Role.ASSISTANT == "assistant"
        assert Role.TOOL == "tool"


class TestMessage:
    """Test Message model."""
    
    def test_basic_message(self):
        """Test creating a basic message."""
        msg = Message(role=Role.USER, content="Hello")
        assert msg.role == Role.USER
        assert msg.content == "Hello"
        assert msg.name is None
    
    def test_message_with_name(self):
        """Test message with optional name."""
        msg = Message(role=Role.TOOL, content="result", name="calculator")
        assert msg.name == "calculator"
    
    def test_message_empty_content_becomes_none(self):
        """Test that empty string content becomes None."""
        msg = Message(role=Role.ASSISTANT, content="")
        assert msg.content is None
    
    def test_message_none_content(self):
        """Test message with None content."""
        msg = Message(role=Role.ASSISTANT, content=None)
        assert msg.content is None
    
    def test_message_from_dict(self):
        """Test creating message from dictionary."""
        data = {"role": "user", "content": "Test"}
        msg = Message(**data)
        assert msg.role == Role.USER
        assert msg.content == "Test"
    
    def test_invalid_role(self):
        """Test that invalid role raises error."""
        with pytest.raises(ValidationError):
            Message(role="invalid", content="test")


class TestChatCompletionRequest:
    """Test ChatCompletionRequest model."""
    
    def test_minimal_request(self):
        """Test minimal valid request."""
        req = ChatCompletionRequest(
            messages=[Message(role=Role.USER, content="Hello")]
        )
        assert len(req.messages) == 1
        assert req.stream is False
        assert req.temperature is None
    
    def test_full_request(self):
        """Test request with all parameters."""
        req = ChatCompletionRequest(
            messages=[Message(role=Role.USER, content="Hello")],
            model="test-model",
            temperature=0.7,
            top_p=0.9,
            n=1,
            stream=True,
            stop=["STOP"],
            max_tokens=100,
            presence_penalty=0.5,
            frequency_penalty=0.5,
            user="user123",
        )
        assert req.model == "test-model"
        assert req.temperature == 0.7
        assert req.stream is True
        assert req.max_tokens == 100
    
    def test_empty_messages_raises_error(self):
        """Test that empty messages list raises error."""
        with pytest.raises(ValidationError):
            ChatCompletionRequest(messages=[])
    
    def test_temperature_bounds(self):
        """Test temperature validation bounds."""
        # Valid
        ChatCompletionRequest(
            messages=[Message(role=Role.USER, content="test")],
            temperature=0.0
        )
        ChatCompletionRequest(
            messages=[Message(role=Role.USER, content="test")],
            temperature=2.0
        )
        
        # Invalid
        with pytest.raises(ValidationError):
            ChatCompletionRequest(
                messages=[Message(role=Role.USER, content="test")],
                temperature=-0.1
            )
        with pytest.raises(ValidationError):
            ChatCompletionRequest(
                messages=[Message(role=Role.USER, content="test")],
                temperature=2.1
            )
    
    def test_max_tokens_bounds(self):
        """Test max_tokens validation."""
        # Valid
        ChatCompletionRequest(
            messages=[Message(role=Role.USER, content="test")],
            max_tokens=1
        )
        
        # Invalid
        with pytest.raises(ValidationError):
            ChatCompletionRequest(
                messages=[Message(role=Role.USER, content="test")],
                max_tokens=0
            )
    
    def test_multiple_messages(self):
        """Test request with conversation history."""
        req = ChatCompletionRequest(
            messages=[
                Message(role=Role.SYSTEM, content="You are helpful"),
                Message(role=Role.USER, content="Hello"),
                Message(role=Role.ASSISTANT, content="Hi there!"),
                Message(role=Role.USER, content="How are you?"),
            ]
        )
        assert len(req.messages) == 4
        assert req.messages[0].role == Role.SYSTEM


class TestUsageInfo:
    """Test UsageInfo model."""
    
    def test_usage_info(self):
        """Test creating usage info."""
        usage = UsageInfo(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30
        )
        assert usage.prompt_tokens == 10
        assert usage.total_tokens == 30


class TestChoice:
    """Test Choice model."""
    
    def test_choice(self):
        """Test creating a choice."""
        from proxy.models import ResponseMessage
        
        choice = Choice(
            index=0,
            message=ResponseMessage(role="assistant", content="Response"),
            finish_reason="stop"
        )
        assert choice.index == 0
        assert choice.finish_reason == "stop"


class TestChatCompletionResponse:
    """Test ChatCompletionResponse model."""
    
    def test_response_auto_fields(self):
        """Test auto-generated fields."""
        from proxy.models import ResponseMessage
        
        resp = ChatCompletionResponse(
            model="test-model",
            choices=[
                Choice(
                    index=0,
                    message=ResponseMessage(role="assistant", content="Hello"),
                )
            ]
        )
        assert resp.object == "chat.completion"
        assert resp.id.startswith("chatcmpl-")
        assert isinstance(resp.created, int)
    
    def test_response_with_usage(self):
        """Test response with usage info."""
        from proxy.models import ResponseMessage
        
        resp = ChatCompletionResponse(
            model="test-model",
            choices=[
                Choice(
                    index=0,
                    message=ResponseMessage(role="assistant", content="Hello"),
                )
            ],
            usage=UsageInfo(
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15
            )
        )
        assert resp.usage is not None
        assert resp.usage.total_tokens == 15


class TestStreamingModels:
    """Test streaming response models."""
    
    def test_delta_message(self):
        """Test delta message."""
        delta = DeltaMessage(content="Hello")
        assert delta.content == "Hello"
        assert delta.role is None
    
    def test_streaming_choice(self):
        """Test streaming choice."""
        choice = StreamingChoice(
            index=0,
            delta=DeltaMessage(content="Hello"),
        )
        assert choice.index == 0
    
    def test_chat_completion_chunk(self):
        """Test streaming chunk."""
        chunk = ChatCompletionChunk(
            model="test-model",
            choices=[
                StreamingChoice(
                    index=0,
                    delta=DeltaMessage(content="Hello"),
                )
            ]
        )
        assert chunk.object == "chat.completion.chunk"
        assert chunk.id.startswith("chatcmpl-")


class TestHealthResponse:
    """Test HealthResponse model."""
    
    def test_healthy_response(self):
        """Test healthy status response."""
        health = HealthResponse(
            status="healthy",
            version="1.0.0",
            compression_enabled=True,
            llm_endpoint="http://localhost:8000",
            uptime_seconds=123.45
        )
        assert health.status == "healthy"
        assert health.uptime_seconds == 123.45
    
    def test_invalid_status(self):
        """Test that invalid status raises error."""
        with pytest.raises(ValidationError):
            HealthResponse(
                status="invalid",
                version="1.0.0",
                compression_enabled=True,
                llm_endpoint="http://localhost:8000",
                uptime_seconds=0.0
            )


class TestErrorResponse:
    """Test ErrorResponse model."""
    
    def test_error_response_creation(self):
        """Test creating error response with factory method."""
        err = ErrorResponse.create(
            message="Invalid request",
            type="invalid_request_error",
            code="missing_field"
        )
        assert err.error["message"] == "Invalid request"
        assert err.error["type"] == "invalid_request_error"
        assert err.error["code"] == "missing_field"
    
    def test_error_response_minimal(self):
        """Test creating minimal error response."""
        err = ErrorResponse.create(message="Something went wrong")
        assert err.error["message"] == "Something went wrong"
        assert err.error["type"] == "api_error"
        assert "code" not in err.error
