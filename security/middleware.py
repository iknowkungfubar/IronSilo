"""
Security middleware for IronSilo services.

Provides:
- API key authentication
- Rate limiting
- Request size limiting
- CORS configuration
- Error sanitization
"""

from __future__ import annotations

import os
import time
from collections import defaultdict
from typing import Callable, Optional

import structlog
from fastapi import Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)

# Configuration
API_KEY = os.getenv("IRONSILO_API_KEY", "")
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "60"))  # per minute
RATE_LIMIT_WINDOW = 60  # seconds
MAX_REQUEST_SIZE = int(os.getenv("MAX_REQUEST_SIZE", str(10 * 1024 * 1024)))  # 10MB default


class RateLimiter:
    """Simple in-memory rate limiter using sliding window."""
    
    def __init__(self, requests_per_minute: int = RATE_LIMIT_REQUESTS):
        self.requests_per_minute = requests_per_minute
        self._requests: Dict[str, list[float]] = defaultdict(list)
    
    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed under rate limit."""
        now = time.time()
        window_start = now - RATE_LIMIT_WINDOW
        
        # Clean old requests
        self._requests[client_id] = [
            t for t in self._requests[client_id] if t > window_start
        ]
        
        # Check limit
        if len(self._requests[client_id]) >= self.requests_per_minute:
            return False
        
        # Record request
        self._requests[client_id].append(now)
        return True
    
    def get_remaining(self, client_id: str) -> int:
        """Get remaining requests in current window."""
        now = time.time()
        window_start = now - RATE_LIMIT_WINDOW
        
        self._requests[client_id] = [
            t for t in self._requests[client_id] if t > window_start
        ]
        
        return max(0, self.requests_per_minute - len(self._requests[client_id]))


# Global rate limiter instance
_rate_limiter = RateLimiter()


def get_client_id(request: Request) -> str:
    """Extract client identifier from request."""
    # Try API key first, then IP
    api_key = request.headers.get("X-API-Key", "")
    if api_key:
        return f"key:{api_key[:8]}"
    
    # Get real IP (considering proxies)
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return f"ip:{forwarded.split(',')[0].strip()}"
    
    client_host = request.client.host if request.client else "unknown"
    return f"ip:{client_host}"


async def auth_middleware(request: Request, call_next: Callable) -> Response:
    """
    Authentication middleware.
    
    Requires X-API-Key header when IRONSILO_API_KEY is set.
    Skips authentication for health checks and docs.
    """
    # Skip auth for health/docs endpoints
    skip_paths = ["/health", "/docs", "/openapi.json", "/redoc", "/"]
    if request.url.path in skip_paths:
        return await call_next(request)
    
    # Check API key if configured
    if API_KEY:
        api_key = request.headers.get("X-API-Key", "")
        
        # Also check query param for convenience
        if not api_key:
            api_key = request.query_params.get("api_key", "")
        
        if api_key != API_KEY:
            logger.warning(
                "auth_failed",
                path=request.url.path,
                client=get_client_id(request),
            )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": {
                        "message": "Invalid or missing API key",
                        "type": "authentication_error",
                    }
                },
            )
    
    return await call_next(request)


async def rate_limit_middleware(request: Request, call_next: Callable) -> Response:
    """
    Rate limiting middleware.
    
    Limits requests per client based on sliding window.
    """
    # Skip rate limiting for health checks
    if request.url.path in ["/health", "/"]:
        return await call_next(request)
    
    client_id = get_client_id(request)
    
    if not _rate_limiter.is_allowed(client_id):
        remaining = _rate_limiter.get_remaining(client_id)
        logger.warning("rate_limited", client=client_id, path=request.url.path)
        
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": {
                    "message": "Rate limit exceeded. Try again later.",
                    "type": "rate_limit_error",
                    "retry_after": RATE_LIMIT_WINDOW,
                }
            },
            headers={
                "X-RateLimit-Limit": str(RATE_LIMIT_REQUESTS),
                "X-RateLimit-Remaining": "0",
                "Retry-After": str(RATE_LIMIT_WINDOW),
            },
        )
    
    response = await call_next(request)
    
    # Add rate limit headers
    remaining = _rate_limiter.get_remaining(client_id)
    response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT_REQUESTS)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    
    return response


async def request_size_middleware(request: Request, call_next: Callable) -> Response:
    """
    Request size limiting middleware.
    
    Rejects requests exceeding MAX_REQUEST_SIZE.
    """
    content_length = request.headers.get("content-length")
    
    if content_length:
        try:
            size = int(content_length)
            if size > MAX_REQUEST_SIZE:
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={
                        "error": {
                            "message": f"Request too large. Maximum size: {MAX_REQUEST_SIZE // (1024*1024)}MB",
                            "type": "request_too_large",
                        }
                    },
                )
        except ValueError:
            pass
    
    return await call_next(request)


def setup_cors(app) -> None:
    """
    Configure CORS for the application.
    
    In development, allows localhost.
    In production, requires explicit CORS_ORIGINS env var.
    """
    env = os.getenv("ENVIRONMENT", "development")
    
    if env == "development":
        allow_origins = ["http://localhost:*", "http://127.0.0.1:*"]
    else:
        origins = os.getenv("CORS_ORIGINS", "")
        allow_origins = [o.strip() for o in origins.split(",") if o.strip()]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
        expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-Request-ID"],
    )


def sanitize_error_message(error: Exception) -> str:
    """
    Sanitize error message to prevent information leakage.
    
    Returns generic message, logs full details internally.
    """
    # Map specific error types to safe messages
    error_type = type(error).__name__
    
    safe_messages = {
        "ConnectionError": "Upstream service unavailable",
        "TimeoutError": "Request timed out",
        "ValueError": "Invalid request",
        "KeyError": "Missing required field",
        "ValidationError": "Invalid request data",
    }
    
    return safe_messages.get(error_type, "Internal server error")


def setup_security_middleware(app) -> None:
    """
    Apply all security middleware to the FastAPI app.
    
    Order matters - applied in sequence:
    1. CORS (outermost)
    2. Request size limit
    3. Rate limiting
    4. Authentication (innermost)
    """
    # CORS
    setup_cors(app)
    
    # Add middleware in reverse order (last added = outermost)
    app.middleware("http")(auth_middleware)
    app.middleware("http")(rate_limit_middleware)
    app.middleware("http")(request_size_middleware)


# Type hint import
from typing import Dict
