"""
IronSilo LLM Proxy - LLMLingua-based prompt compression proxy.

This module provides an OpenAI-compatible API proxy that:
1. Intercepts chat completion requests
2. Compresses prompts using LLMLingua to reduce token usage
3. Forwards compressed requests to the upstream LLM endpoint
4. Returns responses in OpenAI-compatible format

Architecture:
    Client -> Proxy (LLMLingua compression) -> Upstream LLM (LM Studio/Ollama/Lemonade)

Features:
    - Automatic prompt compression for messages > 1000 chars
    - Streaming response support
    - Health check endpoint
    - Structured logging
    - Request/response validation with Pydantic
"""

from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Optional

import httpx
import structlog
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, StreamingResponse

# Import models - handle both package and standalone execution
try:
    from .models import (
        ChatCompletionRequest,
        ChatCompletionResponse,
        Choice,
        ErrorResponse,
        HealthResponse,
        Message,
        ResponseMessage,
    )
except ImportError:
    from models import (
        ChatCompletionRequest,
        ChatCompletionResponse,
        Choice,
        ErrorResponse,
        HealthResponse,
        Message,
        ResponseMessage,
    )

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger(__name__)

# Configuration
LLM_ENDPOINT = os.getenv("LLM_ENDPOINT", "http://host.docker.internal:8000/v1/chat/completions")
COMPRESSION_THRESHOLD = int(os.getenv("COMPRESSION_THRESHOLD", "1000"))
COMPRESSION_RATE = float(os.getenv("COMPRESSION_RATE", "0.6"))
PROXY_VERSION = os.getenv("PROXY_VERSION", "2.0.0")

# Global state for health checks
_start_time: float = 0.0
_compressor: Optional[Any] = None
_compression_enabled: bool = False


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    
    Handles initialization of LLMLingua compressor on startup
    and cleanup on shutdown.
    """
    global _start_time, _compressor, _compression_enabled
    
    _start_time = time.time()
    
    logger.info("proxy_starting", llm_endpoint=LLM_ENDPOINT)
    
    try:
        # Import and initialize LLMLingua
        from llmlingua import PromptCompressor
        
        logger.info("loading_llmlingua", model="microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank")
        
        _compressor = PromptCompressor(
            model_name="microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank",
            use_llmlingua2=True,
            device_map="cpu",
        )
        _compression_enabled = True
        
        logger.info("llmlingua_loaded", compression_enabled=True)
        
    except ImportError as e:
        logger.warning("llmlingua_not_available", error=str(e), compression_enabled=False)
        _compression_enabled = False
        
    except Exception as e:
        logger.error("llmlingua_load_failed", error=str(e), exc_info=True)
        _compression_enabled = False
    
    logger.info("proxy_started", version=PROXY_VERSION)
    
    yield
    
    # Cleanup
    logger.info("proxy_shutting_down")


# Create FastAPI application
app = FastAPI(
    title="IronSilo LLM Proxy",
    description="OpenAI-compatible proxy with LLMLingua prompt compression",
    version=PROXY_VERSION,
    lifespan=lifespan,
    docs_url=None,  # Disable Swagger UI in production
    redoc_url=None,  # Disable ReDoc in production
)


def _compress_content(content: str) -> str:
    """
    Compress content using LLMLingua if available.
    
    Args:
        content: Original content to compress
        
    Returns:
        Compressed content, or original if compression fails/disabled
    """
    if not _compression_enabled or not _compressor:
        return content
    
    if len(content) <= COMPRESSION_THRESHOLD:
        return content
    
    try:
        start_time = time.time()
        
        result = _compressor.compress_prompt(
            content,
            rate=COMPRESSION_RATE,
            force_tokens=["system", "user", "assistant", "```", "def", "class"],
        )
        
        compressed = result.get("compressed_prompt", content)
        original_len = len(content)
        compressed_len = len(compressed)
        ratio = compressed_len / original_len if original_len > 0 else 1.0
        elapsed = time.time() - start_time
        
        logger.info(
            "compression_complete",
            original_chars=original_len,
            compressed_chars=compressed_len,
            compression_ratio=f"{ratio:.2%}",
            elapsed_ms=f"{elapsed * 1000:.1f}",
        )
        
        return compressed
        
    except Exception as e:
        logger.warning("compression_failed", error=str(e))
        return content


def _process_messages(messages: list[Message]) -> list[Dict[str, Any]]:
    """
    Process messages, applying compression where needed.
    
    Args:
        messages: List of validated Message objects
        
    Returns:
        List of message dicts ready for upstream
    """
    try:
        from .models import Role
    except ImportError:
        from models import Role
    
    processed = []
    
    for msg in messages:
        msg_dict = msg.model_dump(exclude_none=True)
        
        # Convert role enum to string value (e.g., Role.USER -> "user")
        if "role" in msg_dict:
            role = msg_dict["role"]
            if isinstance(role, Role):
                msg_dict["role"] = role.value
            elif hasattr(role, "value"):
                msg_dict["role"] = role.value
        
        # Compress content if present and long enough
        if msg_dict.get("content") and len(msg_dict["content"]) > COMPRESSION_THRESHOLD:
            msg_dict["content"] = _compress_content(msg_dict["content"])
        
        processed.append(msg_dict)
    
    return processed


@app.get("/health")
async def health_check() -> HealthResponse:
    """
    Health check endpoint.
    
    Returns:
        Health status including compression availability and uptime
    """
    uptime = time.time() - _start_time
    
    return HealthResponse(
        status="healthy" if _compression_enabled else "degraded",
        version=PROXY_VERSION,
        compression_enabled=_compression_enabled,
        llm_endpoint=LLM_ENDPOINT,
        uptime_seconds=uptime,
    )


@app.post("/api/v1/chat/completions", response_model=None)
async def chat_completions(request: Request):
    """
    OpenAI-compatible chat completions endpoint.
    
    This endpoint:
    1. Validates the request using Pydantic models
    2. Compresses long messages using LLMLingua
    3. Forwards to the upstream LLM
    4. Returns the response in OpenAI format
    
    Args:
        request: The incoming HTTP request
        
    Returns:
        Chat completion response (streaming or non-streaming)
    """
    request_start = time.time()
    request_id = f"req-{request_start:.0f}"
    
    logger.info("request_received", request_id=request_id, path=request.url.path)
    
    try:
        # Parse and validate request body
        body = await request.json()
        
        try:
            req = ChatCompletionRequest(**body)
        except Exception as e:
            logger.error("validation_failed", request_id=request_id, error=str(e))
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content=ErrorResponse.create(
                    message=f"Invalid request: {e}",
                    type="invalid_request_error",
                ).model_dump(),
            )
        
        # Build upstream request payload
        upstream_payload: Dict[str, Any] = {
            "messages": _process_messages(req.messages),
            "stream": req.stream,
        }
        
        # Add optional parameters
        if req.model:
            upstream_payload["model"] = req.model
        if req.temperature is not None:
            upstream_payload["temperature"] = req.temperature
        if req.top_p is not None:
            upstream_payload["top_p"] = req.top_p
        if req.max_tokens is not None:
            upstream_payload["max_tokens"] = req.max_tokens
        if req.stop is not None:
            upstream_payload["stop"] = req.stop
        if req.presence_penalty is not None:
            upstream_payload["presence_penalty"] = req.presence_penalty
        if req.frequency_penalty is not None:
            upstream_payload["frequency_penalty"] = req.frequency_penalty
        
        # Add any extra fields from passthrough
        upstream_payload.update(req.extra_fields)
        
        logger.info(
            "forwarding_request",
            request_id=request_id,
            upstream_url=LLM_ENDPOINT,
            stream=req.stream,
            message_count=len(req.messages),
        )
        
        # Handle streaming vs non-streaming
        if req.stream:
            return StreamingResponse(
                _stream_generator(upstream_payload, request_id),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Request-ID": request_id,
                },
            )
        else:
            response = await _non_stream_request(upstream_payload, request_id)
            
            elapsed = time.time() - request_start
            logger.info(
                "request_complete",
                request_id=request_id,
                elapsed_ms=f"{elapsed * 1000:.1f}",
            )
            
            return JSONResponse(content=response)
            
    except Exception as e:
        logger.error("request_failed", request_id=request_id, error=str(e), exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse.create(
                message=f"Internal server error: {e}",
                type="api_error",
                code="internal_error",
            ).model_dump(),
        )


async def _non_stream_request(
    payload: Dict[str, Any],
    request_id: str,
) -> Dict[str, Any]:
    """
    Make a non-streaming request to the upstream LLM.
    
    Args:
        payload: The request payload
        request_id: Request identifier for logging
        
    Returns:
        Response dictionary
    """
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            LLM_ENDPOINT,
            json=payload,
            headers={"X-Request-ID": request_id},
        )
        response.raise_for_status()
        return response.json()


async def _stream_generator(
    payload: Dict[str, Any],
    request_id: str,
) -> AsyncGenerator[bytes, None]:
    """
    Generate streaming response chunks from upstream LLM.
    
    Args:
        payload: The request payload
        request_id: Request identifier for logging
        
    Yields:
        Raw bytes from the upstream stream
    """
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream(
                "POST",
                LLM_ENDPOINT,
                json=payload,
                headers={"X-Request-ID": request_id},
            ) as response:
                response.raise_for_status()
                
                async for chunk in response.aiter_raw():
                    yield chunk
                    
    except httpx.TimeoutException as e:
        logger.error("stream_timeout", request_id=request_id, error=str(e))
        yield f"data: {ErrorResponse.create(message='Upstream timeout', type='api_error').model_dump_json()}\n\n".encode()
        
    except Exception as e:
        logger.error("stream_error", request_id=request_id, error=str(e), exc_info=True)
        yield f"data: {ErrorResponse.create(message=str(e), type='api_error').model_dump_json()}\n\n".encode()


# Re-export for testing
__all__ = ["app", "_compress_content", "_process_messages"]
