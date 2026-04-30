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
    - API key authentication
    - Rate limiting
    - Request size limits
    - CORS configuration
    - Error sanitization
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

# Import security middleware
try:
    from ..security.middleware import (
        sanitize_error_message,
        setup_security_middleware,
    )
except ImportError:
    try:
        from security.middleware import (
            sanitize_error_message,
            setup_security_middleware,
        )
    except ImportError:
        # Fallback if security module not available
        def sanitize_error_message(error: Exception) -> str:
            return "Internal server error"
        
        def setup_security_middleware(app: FastAPI) -> None:
            pass

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

# Retry configuration for upstream LLM requests
RETRY_MAX_ATTEMPTS = int(os.getenv("RETRY_MAX_ATTEMPTS", "3"))
RETRY_BASE_DELAY = float(os.getenv("RETRY_BASE_DELAY", "1.0"))
RETRY_MAX_DELAY = float(os.getenv("RETRY_MAX_DELAY", "10.0"))
RETRY_STATUS_CODES = [500, 502, 503, 504]

# KV Cache configuration
KV_CACHE_ENABLED = os.getenv("KV_CACHE_ENABLED", "false").lower() == "true"
KV_CACHE_MAX_SIZE = int(os.getenv("KV_CACHE_MAX_SIZE", "1000"))
KV_CACHE_TTL_SECONDS = int(os.getenv("KV_CACHE_TTL_SECONDS", "3600"))

# Global cache instance (lazy initialization)
_kv_cache = None


def _get_kv_cache():
    """Get or create the global KV cache instance."""
    global _kv_cache
    if _kv_cache is None:
        from cache.kv_store import create_kv_cache
        _kv_cache = create_kv_cache(max_size=KV_CACHE_MAX_SIZE)
    return _kv_cache

CIRCUIT_BREAKER_FAILURE_THRESHOLD = int(os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "5"))
CIRCUIT_BREAKER_TIMEOUT = float(os.getenv("CIRCUIT_BREAKER_TIMEOUT", "30.0"))

# HTTP Client connection pool settings
HTTP_CLIENT_MAX_CONNECTIONS = int(os.getenv("HTTP_CLIENT_MAX_CONNECTIONS", "100"))
HTTP_CLIENT_MAX_KEEPALIVE = int(os.getenv("HTTP_CLIENT_MAX_KEEPALIVE", "20"))
HTTP_CLIENT_TIMEOUT = float(os.getenv("HTTP_CLIENT_TIMEOUT", "60.0"))


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for proxy reliability.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests fail fast
    - HALF_OPEN: Testing if service recovered
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(self, failure_threshold: int = 5, timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: float = 0.0
        self.state = self.CLOSED
        self._lock = __import__("asyncio").Lock()

    async def can_proceed(self) -> bool:
        """Check if request can proceed through circuit breaker."""
        async with self._lock:
            if self.state == self.CLOSED:
                return True

            if self.state == self.OPEN:
                if __import__("time").time() - self.last_failure_time >= self.timeout:
                    self.state = self.HALF_OPEN
                    logger.info("circuit_breaker_half_open")
                    return True
                return False

            if self.state == self.HALF_OPEN:
                return True

            return False

    async def record_success(self) -> None:
        """Record successful request."""
        async with self._lock:
            if self.state == self.HALF_OPEN:
                self.state = self.CLOSED
                self.failure_count = 0
                logger.info("circuit_breaker_closed")
            else:
                self.failure_count = 0

    async def record_failure(self) -> None:
        """Record failed request."""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = __import__("time").time()

            if self.state == self.HALF_OPEN:
                self.state = self.OPEN
                logger.warning("circuit_breaker_reopened")
            elif self.failure_count >= self.failure_threshold:
                self.state = self.OPEN
                logger.warning("circuit_breaker_opened", failures=self.failure_count)

    @property
    def status(self) -> dict[str, Any]:
        """Return circuit breaker status for monitoring."""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "timeout_seconds": self.timeout,
        }


circuit_breaker = CircuitBreaker(
    failure_threshold=CIRCUIT_BREAKER_FAILURE_THRESHOLD,
    timeout=CIRCUIT_BREAKER_TIMEOUT,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Handles initialization of LLMLingua compressor on startup
    and cleanup on shutdown.
    """
    global _compressor, _compression_enabled, _start_time

    _start_time = time.time()
    app.state.start_time = _start_time
    app.state.compressor = None
    app.state.compression_enabled = False

    logger.info("proxy_starting", llm_endpoint=LLM_ENDPOINT)

    limits = httpx.Limits(
        max_connections=HTTP_CLIENT_MAX_CONNECTIONS,
        max_keepalive_connections=HTTP_CLIENT_MAX_KEEPALIVE,
    )
    app.state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(HTTP_CLIENT_TIMEOUT),
        limits=limits,
    )
    logger.info("http_client_initialized", max_connections=HTTP_CLIENT_MAX_CONNECTIONS)

    try:
        from llmlingua import PromptCompressor

        logger.info("loading_llmlingua", model="microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank")

        _compressor = PromptCompressor(
            model_name="microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank",
            use_llmlingua2=True,
            device_map="cpu",
        )
        app.state.compressor = _compressor
        _compression_enabled = True
        app.state.compression_enabled = True

        logger.info("llmlingua_loaded", compression_enabled=True)

    except ImportError as e:
        logger.warning("llmlingua_not_available", error=str(e), compression_enabled=False)
        app.state.compression_enabled = False
        _compression_enabled = False

    except Exception as e:
        logger.error("llmlingua_load_failed", error=str(e), exc_info=True)
        app.state.compression_enabled = False
        _compression_enabled = False

    logger.info("proxy_started", version=PROXY_VERSION)

    yield

    logger.info("proxy_shutting_down")
    await app.state.http_client.aclose()
    app.state.compressor = None
    _compressor = None


# Create FastAPI application
app = FastAPI(
    title="IronSilo LLM Proxy",
    description="OpenAI-compatible proxy with LLMLingua prompt compression",
    version=PROXY_VERSION,
    lifespan=lifespan,
    docs_url=None,  # Disable Swagger UI in production
    redoc_url=None,  # Disable ReDoc in production
)

# Apply security middleware
setup_security_middleware(app)


def _sanitize_content(content: str) -> str:
    """
    Sanitize user content by removing dangerous characters.

    Removes:
    - Null bytes (\\x00)
    - Control characters (except newline, tab, carriage return)
    - Vertical tab, form feed
    - Invalid Unicode surrogates

    Args:
        content: Raw user content

    Returns:
        Sanitized content safe for LLM
    """
    if not content:
        return content

    import re

    content = content.replace('\x00', '')
    content = content.replace('\u0000', '')

    content = re.sub(r'[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]', '', content)

    content = re.sub(r'[\ud800-\udfff]', '', content)

    return content.strip()


def _compress_content(content: str, compressor: Any = None, enabled: bool = False) -> str:
    """
    Compress content using LLMLingua if available.
    
    Args:
        content: Original content to compress
        compressor: LLMLingua compressor instance (uses module-level _compressor if None)
        enabled: Whether compression is enabled (uses module-level _compression_enabled if False)
        
    Returns:
        Compressed content, or original if compression fails/disabled
    """
    # Use module-level defaults if not explicitly provided
    if compressor is None:
        compressor = _compressor
    if enabled is False:
        enabled = _compression_enabled
    
    if not enabled or not compressor:
        return content
    
    if len(content) <= COMPRESSION_THRESHOLD:
        return content
    
    try:
        start_time = time.time()
        
        result = compressor.compress_prompt(
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


def _process_messages(messages: list[Message], compressor: Any = None, enabled: bool = False, bypass_compression: bool = False) -> list[Dict[str, Any]]:
    """
    Process messages, applying compression where needed.

    Args:
        messages: List of validated Message objects
        compressor: LLMLingua compressor instance
        enabled: Whether compression is enabled
        bypass_compression: If True, skip compression entirely

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

        # Sanitize content first, then compress if long enough (unless bypass is set)
        if msg_dict.get("content"):
            msg_dict["content"] = _sanitize_content(msg_dict["content"])
            if not bypass_compression and len(msg_dict["content"]) > COMPRESSION_THRESHOLD:
                msg_dict["content"] = _compress_content(msg_dict["content"], compressor, enabled)

        processed.append(msg_dict)

    return processed


@app.get("/health")
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns:
        Health status including compression availability and uptime
    """
    start_time = getattr(app.state, "start_time", time.time())
    compression_enabled = getattr(app.state, "compression_enabled", False)

    uptime = time.time() - start_time

    return HealthResponse(
        status="healthy" if compression_enabled else "degraded",
        version=PROXY_VERSION,
        compression_enabled=compression_enabled,
        llm_endpoint=LLM_ENDPOINT,
        uptime_seconds=uptime,
    )


@app.get("/metrics")
async def metrics() -> JSONResponse:
    """Prometheus-compatible metrics endpoint."""
    uptime = time.time() - getattr(app.state, "start_time", time.time())
    cb = circuit_breaker

    return JSONResponse({
        "metrics": {
            "info": {
                "version": PROXY_VERSION,
                "compression_enabled": getattr(app.state, "compression_enabled", False),
                "llm_endpoint": LLM_ENDPOINT,
            },
            "uptime_seconds": uptime,
            "circuit_breaker": cb.status,
            "compression": {
                "threshold": COMPRESSION_THRESHOLD,
                "rate": COMPRESSION_RATE,
            },
            "retry": {
                "max_attempts": RETRY_MAX_ATTEMPTS,
                "base_delay": RETRY_BASE_DELAY,
                "max_delay": RETRY_MAX_DELAY,
            },
            "timestamp": time.time(),
        }
    })


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
                    message="Invalid request data",  # Sanitized
                    type="invalid_request_error",
                ).model_dump(),
            )

        # Check if compression should be bypassed
        bypass_compression = False
        x_bypass = request.headers.get("X-Bypass-Compression", "").lower()
        if x_bypass == "true":
            bypass_compression = True
            logger.info("compression_bypassed", request_id=request_id, reason="X-Bypass-Compression header")
        elif req.model and any(keyword in req.model.lower() for keyword in ["vision", "dom"]):
            bypass_compression = True
            logger.info("compression_bypassed", request_id=request_id, reason="model contains vision/dom", model=req.model)

        # Build upstream request payload
        upstream_payload: Dict[str, Any] = {
            "messages": _process_messages(req.messages, app.state.compressor, app.state.compression_enabled, bypass_compression),
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
                _stream_generator(upstream_payload, request_id, request.app.state.http_client),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Request-ID": request_id,
                },
            )
        else:
            response = await _non_stream_request(upstream_payload, request_id, request.app.state.http_client)
            
            elapsed = time.time() - request_start
            logger.info(
                "request_complete",
                request_id=request_id,
                elapsed_ms=f"{elapsed * 1000:.1f}",
            )
            
            return JSONResponse(content=response)
            
    except Exception as e:
        logger.error("request_failed", request_id=request_id, error=str(e), exc_info=True)
        safe_message = sanitize_error_message(e)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse.create(
                message=safe_message,  # Sanitized error message
                type="api_error",
                code="internal_error",
            ).model_dump(),
        )


async def _retry_with_backoff(
    payload: Dict[str, Any],
    request_id: str,
    client: httpx.AsyncClient,
) -> Dict[str, Any]:
    """
    Make a request to upstream LLM with retry and exponential backoff.

    Args:
        payload: The request payload
        request_id: Request identifier for logging
        client: Shared httpx AsyncClient for connection pooling

    Returns:
        Response dictionary

    Raises:
        Exception: If all retry attempts fail
    """
    import asyncio

    last_exception = None

    for attempt in range(RETRY_MAX_ATTEMPTS):
        try:
            response = await client.post(
                LLM_ENDPOINT,
                json=payload,
                headers={"X-Request-ID": request_id},
            )

            if response.status_code in RETRY_STATUS_CODES:
                if attempt < RETRY_MAX_ATTEMPTS - 1:
                    delay = min(RETRY_BASE_DELAY * (2 ** attempt), RETRY_MAX_DELAY)
                    logger.warning(
                        "retry_attempt",
                        request_id=request_id,
                        attempt=attempt + 1,
                        status_code=response.status_code,
                        delay=delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    response.raise_for_status()

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if 400 <= e.response.status_code < 500:
                raise
            last_exception = e
        except httpx.TimeoutException as e:
            last_exception = e
            if attempt < RETRY_MAX_ATTEMPTS - 1:
                delay = min(RETRY_BASE_DELAY * (2 ** attempt), RETRY_MAX_DELAY)
                logger.warning(
                    "retry_timeout",
                    request_id=request_id,
                    attempt=attempt + 1,
                    delay=delay,
                )
                await asyncio.sleep(delay)
                continue
        except Exception as e:
            last_exception = e
            if attempt < RETRY_MAX_ATTEMPTS - 1:
                delay = min(RETRY_BASE_DELAY * (2 ** attempt), RETRY_MAX_DELAY)
                logger.warning(
                    "retry_error",
                    request_id=request_id,
                    attempt=attempt + 1,
                    error=str(e),
                    delay=delay,
                )
                await asyncio.sleep(delay)
                continue

    if last_exception:
        raise last_exception
    raise Exception("Max retries exceeded")


async def _non_stream_request(
    payload: Dict[str, Any],
    request_id: str,
    client: httpx.AsyncClient,
) -> Dict[str, Any]:
    """
    Make a non-streaming request to the upstream LLM with circuit breaker and retry.

    Args:
        payload: The request payload
        request_id: Request identifier for logging
        client: Shared httpx AsyncClient for connection pooling

    Returns:
        Response dictionary

    Raises:
        Exception: If circuit breaker is open or all retries fail
    """
    if not await circuit_breaker.can_proceed():
        logger.warning("circuit_breaker_open", request_id=request_id)
        raise Exception("Circuit breaker is OPEN - upstream service unavailable")

    # Check KV cache first (only for non-streaming)
    cache = _get_kv_cache()
    if KV_CACHE_ENABLED:
        messages = payload.get("messages", [])
        model = payload.get("model", "")
        temperature = payload.get("temperature", 0.7)
        max_tokens = payload.get("max_tokens", 4096)

        cached_response = await cache.get_response(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        if cached_response is not None:
            logger.info("cache_hit", request_id=request_id)
            await circuit_breaker.record_success()
            return cached_response

        logger.info("cache_miss", request_id=request_id)

    try:
        result = await _retry_with_backoff(payload, request_id, client)

        # Store in KV cache if enabled
        if KV_CACHE_ENABLED:
            messages = payload.get("messages", [])
            model = payload.get("model", "")
            temperature = payload.get("temperature", 0.7)
            max_tokens = payload.get("max_tokens", 4096)

            await cache.set_response(
                messages=messages,
                response=result,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        await circuit_breaker.record_success()
        return result
    except Exception as e:
        await circuit_breaker.record_failure()
        raise


async def _stream_generator(
    payload: Dict[str, Any],
    request_id: str,
    client: httpx.AsyncClient,
) -> AsyncGenerator[bytes, None]:
    """
    Generate streaming response chunks from upstream LLM.

    Args:
        payload: The request payload
        request_id: Request identifier for logging
        client: Shared httpx AsyncClient for connection pooling

    Yields:
        Raw bytes from the upstream stream
    """
    try:
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
        yield f"data: {ErrorResponse.create(message='Request timed out', type='api_error').model_dump_json()}\n\n".encode()

    except Exception as e:
        logger.error("stream_error", request_id=request_id, error=str(e), exc_info=True)
        safe_message = sanitize_error_message(e)
        yield f"data: {ErrorResponse.create(message=safe_message, type='api_error').model_dump_json()}\n\n".encode()


# Re-export for testing
__all__ = ["app", "_compress_content", "_process_messages", "circuit_breaker", "CircuitBreaker"]


# Module-level variables for backward compatibility with tests
# Tests may set/access these directly; they're synced with app.state
_compressor = None
_compression_enabled = False
_start_time = 0.0


def _sync_from_app_state() -> None:
    """Sync module-level variables from app.state if available."""
    global _compressor, _compression_enabled, _start_time
    
    if hasattr(app.state, "compressor") and app.state.compressor is not None:
        _compressor = app.state.compressor
    if hasattr(app.state, "compression_enabled"):
        _compression_enabled = app.state.compression_enabled
    if hasattr(app.state, "start_time") and app.state.start_time > 0:
        _start_time = app.state.start_time
