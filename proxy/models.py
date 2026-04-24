"""
Pydantic models for the IronSilo LLM Proxy.

This module defines request/response schemas for the OpenAI-compatible API,
ensuring strict validation and type safety for all proxy communications.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class Role(str, Enum):
    """Message roles in a chat conversation."""
    
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Message(BaseModel):
    """A single message in a chat conversation."""
    
    role: Role = Field(..., description="The role of the message sender")
    content: Optional[str] = Field(
        default=None,
        description="The message content (can be None for assistant messages with tool calls)"
    )
    name: Optional[str] = Field(
        default=None,
        description="Optional name for the message sender"
    )
    tool_calls: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Tool calls made by the assistant"
    )
    tool_call_id: Optional[str] = Field(
        default=None,
        description="ID of the tool call this message is responding to"
    )
    
    @field_validator("content")
    @classmethod
    def validate_content(cls, v: Optional[str]) -> Optional[str]:
        """Ensure content is not empty string if provided."""
        if v == "":
            return None
        return v


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request."""
    
    messages: List[Message] = Field(
        ...,
        min_length=1,
        description="List of messages in the conversation"
    )
    model: Optional[str] = Field(
        default=None,
        description="Model identifier (ignored by proxy, passed to upstream)"
    )
    temperature: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Sampling temperature between 0 and 2"
    )
    top_p: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling parameter"
    )
    n: Optional[int] = Field(
        default=None,
        ge=1,
        le=128,
        description="Number of completions to generate"
    )
    stream: bool = Field(
        default=False,
        description="Whether to stream partial responses"
    )
    stop: Optional[Union[str, List[str]]] = Field(
        default=None,
        description="Stop sequences for generation"
    )
    max_tokens: Optional[int] = Field(
        default=None,
        ge=1,
        description="Maximum tokens to generate"
    )
    presence_penalty: Optional[float] = Field(
        default=None,
        ge=-2.0,
        le=2.0,
        description="Presence penalty for repetition"
    )
    frequency_penalty: Optional[float] = Field(
        default=None,
        ge=-2.0,
        le=2.0,
        description="Frequency penalty for repetition"
    )
    user: Optional[str] = Field(
        default=None,
        description="Optional user identifier for tracking"
    )
    
    # Extra fields that may be passed through to upstream
    # This field is populated automatically from any extra fields in the input
    extra_fields: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional fields to pass through to the upstream LLM"
    )
    
    model_config = {"extra": "allow"}
    
    @model_validator(mode="before")
    @classmethod
    def extract_extra_fields(cls, data: Any) -> Any:
        """Extract extra fields and store them in extra_fields."""
        if isinstance(data, dict):
            # Known fields that should not go into extra_fields
            known_fields = {
                "messages", "model", "temperature", "top_p", "n", "stream",
                "stop", "max_tokens", "presence_penalty", "frequency_penalty",
                "user", "extra_fields"
            }
            
            # Find extra fields
            extra = {k: v for k, v in data.items() if k not in known_fields}
            
            # Add to extra_fields dict
            if extra:
                if "extra_fields" not in data:
                    data["extra_fields"] = {}
                elif not isinstance(data["extra_fields"], dict):
                    data["extra_fields"] = {}
                
                # Merge extra fields (explicit extra_fields takes precedence)
                for k, v in extra.items():
                    if k not in data["extra_fields"]:
                        data["extra_fields"][k] = v
        
        return data


class UsageInfo(BaseModel):
    """Token usage information."""
    
    prompt_tokens: int = Field(..., description="Tokens in the prompt")
    completion_tokens: int = Field(..., description="Tokens in the completion")
    total_tokens: int = Field(..., description="Total tokens used")


class ResponseMessage(BaseModel):
    """Response message from the assistant."""
    
    role: Literal["assistant"] = "assistant"
    content: Optional[str] = Field(
        default=None,
        description="The assistant's response content"
    )
    tool_calls: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Tool calls made by the assistant"
    )


class Choice(BaseModel):
    """A single completion choice."""
    
    index: int = Field(..., description="Index of this choice")
    message: ResponseMessage = Field(..., description="The response message")
    finish_reason: Optional[str] = Field(
        default=None,
        description="Reason the generation stopped"
    )


class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response."""
    
    id: str = Field(
        default_factory=lambda: f"chatcmpl-{__import__('uuid').uuid4().hex[:12]}",
        description="Unique identifier for this completion"
    )
    object: Literal["chat.completion"] = "chat.completion"
    created: int = Field(
        default_factory=lambda: int(__import__('time').time()),
        description="Unix timestamp of creation"
    )
    model: str = Field(..., description="Model used for generation")
    choices: List[Choice] = Field(
        ...,
        min_length=1,
        description="List of completion choices"
    )
    usage: Optional[UsageInfo] = Field(
        default=None,
        description="Token usage information"
    )


class DeltaMessage(BaseModel):
    """Streaming delta message."""
    
    role: Optional[Literal["assistant"]] = None
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


class StreamingChoice(BaseModel):
    """A single streaming completion choice."""
    
    index: int = Field(..., description="Index of this choice")
    delta: DeltaMessage = Field(..., description="The delta message")
    finish_reason: Optional[str] = None


class ChatCompletionChunk(BaseModel):
    """OpenAI-compatible streaming chunk."""
    
    id: str = Field(
        default_factory=lambda: f"chatcmpl-{__import__('uuid').uuid4().hex[:12]}",
        description="Unique identifier for this completion"
    )
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    created: int = Field(
        default_factory=lambda: int(__import__('time').time()),
        description="Unix timestamp of creation"
    )
    model: str = Field(..., description="Model used for generation")
    choices: List[StreamingChoice] = Field(
        ...,
        min_length=1,
        description="List of streaming choices"
    )


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        ...,
        description="Overall health status"
    )
    version: str = Field(..., description="Proxy version")
    compression_enabled: bool = Field(
        ...,
        description="Whether LLMLingua compression is active"
    )
    llm_endpoint: str = Field(
        ...,
        description="Configured upstream LLM endpoint"
    )
    uptime_seconds: float = Field(
        ...,
        description="Seconds since proxy started"
    )


class ErrorResponse(BaseModel):
    """Error response."""
    
    error: Dict[str, Any] = Field(
        ...,
        description="Error details"
    )
    
    @classmethod
    def create(
        cls,
        message: str,
        type: str = "api_error",
        code: Optional[str] = None,
    ) -> ErrorResponse:
        """Create an error response."""
        error_data: Dict[str, Any] = {
            "message": message,
            "type": type,
        }
        if code:
            error_data["code"] = code
        return cls(error=error_data)
