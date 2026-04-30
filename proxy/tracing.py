"""
OpenTelemetry distributed tracing for IronSilo.

This module provides tracing instrumentation for:
- HTTP requests (proxy)
- Database operations (genesys)
- Inter-service communication
- Browser swarm operations

Trace Context Propagation:
    X-Request-ID header carries trace context across services

Usage:
    from proxy.tracing import tracer, setup_tracing, trace_function

    # Initialize at app startup
    setup_tracing("llm-proxy")

    # Use context manager
    with tracer.span("my-operation", headers=request.headers):
        # do work
        pass

    # Use decorator
    @trace_function("my-function")
    async def my_async_function():
        pass
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, Dict, Optional

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
    from opentelemetry.trace import Status, StatusCode
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    trace = None

if TYPE_CHECKING:
    from fastapi import Request

import structlog

logger = structlog.get_logger(__name__)

TRACING_ENABLED = os.getenv("TRACING_ENABLED", "false").lower() == "true"
TRACING_CONSOLE_EXPORT = os.getenv("TRACING_CONSOLE_EXPORT", "false").lower() == "true"
SERVICE_NAME_VAL = os.getenv("OTEL_SERVICE_NAME", "ironsilo")


class IronSiloTracer:
    """IronSilo distributed tracing wrapper."""

    _instance: Optional[IronSiloTracer] = None
    _tracer: Optional[Any] = None
    _propagator = None

    def __new__(cls) -> IronSiloTracer:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self, service_name: str = SERVICE_NAME_VAL) -> None:
        """Initialize the tracer provider."""
        if not OTEL_AVAILABLE:
            logger.warning("opentelemetry_not_installed", message="Install opentelemetry-api and opentelemetry-sdk packages for tracing")
            return

        resource = Resource.create({
            SERVICE_NAME: service_name,
            SERVICE_VERSION: os.getenv("OTEL_SERVICE_VERSION", "2.1.0"),
        })

        provider = TracerProvider(resource=resource)

        if TRACING_CONSOLE_EXPORT or os.getenv("ENVIRONMENT", "production") != "production":
            console_exporter = ConsoleSpanExporter()
            span_processor = BatchSpanProcessor(console_exporter)
            provider.add_span_processor(span_processor)

        trace.set_tracer_provider(provider)
        self._tracer = trace.get_tracer(__name__)
        self._propagator = TraceContextTextMapPropagator()

        logger.info("tracing_initialized", service=service_name)

    def get_tracer(self):
        """Get the tracer instance."""
        if self._tracer is None:
            self.initialize()
        return self._tracer

    def extract_context(self, headers: Dict[str, str]) -> Optional[Any]:
        """Extract trace context from HTTP headers."""
        if not OTEL_AVAILABLE or self._propagator is None:
            return None
        try:
            return self._propagator.extract(headers)
        except Exception as e:
            logger.debug("trace_context_extraction_failed", error=str(e))
            return None

    def create_span(self, name: str, context: Optional[Any] = None):
        """Create a new span."""
        tracer = self.get_tracer()
        if tracer is None:
            return NoOpSpan()

        if context is not None:
            return tracer.start_span(name, context=context)
        return tracer.start_span(name)

    def start_as_child(self, name: str, parent_span: Any) -> Any:
        """Start a child span from a parent span."""
        if not OTEL_AVAILABLE or parent_span is None:
            return NoOpSpan()
        tracer = self.get_tracer()
        if tracer is None:
            return NoOpSpan()
        return tracer.start_span(name, parent=parent_span)

    def span(self, name: str, headers: Optional[Dict[str, str]] = None):
        """Context manager for creating a span with context propagation."""
        context = self.extract_context(headers) if headers else None
        span = self.create_span(name, context)
        return SpanContextManager(span)


class SpanContextManager:
    """Context manager for span lifecycle."""

    def __init__(self, span: Any):
        self._span = span
        self._entered = False

    def __enter__(self):
        self._entered = True
        return self._span

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._entered and self._span is not None:
            if OTEL_AVAILABLE and self._span is not None:
                if exc_type is not None:
                    from opentelemetry.trace import Status, StatusCode
                    self._span.set_status(Status(StatusCode.ERROR, str(exc_val)))
                    self._span.record_exception(exc_val)
                self._span.end()
        return False


class NoOpSpan:
    """No-operation span when tracing is not available."""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        pass

    def record_exception(self, exception: Exception) -> None:
        pass

    def set_status(self, status: Any) -> None:
        pass

    def end(self) -> None:
        pass


tracer = IronSiloTracer()


def setup_tracing(service_name: str = SERVICE_NAME_VAL) -> None:
    """Setup tracing for the application."""
    tracer.initialize(service_name)


def get_trace_context_from_request(request: "Request") -> Optional[Any]:
    """Extract trace context from FastAPI request headers."""
    if not hasattr(request, "headers"):
        return None
    headers = dict(request.headers)
    return tracer.extract_context(headers)


def trace_span(name: str, headers: Optional[Dict[str, str]] = None):
    """Context manager for tracing a span with headers for context propagation."""
    return tracer.span(name, headers=headers)


def trace_function(name: Optional[str] = None):
    """Decorator to trace a function."""
    def decorator(func):
        span_name = name or f"{func.__module__}.{func.__name__}"

        def sync_wrapper(*args, **kwargs):
            with tracer.span(span_name) as span:
                return func(*args, **kwargs)

        async def async_wrapper(*args, **kwargs):
            with tracer.span(span_name) as span:
                return await func(*args, **kwargs)

        if hasattr(func, '__wrapped__'):
            return func

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


class TracingMiddleware:
    """FastAPI middleware that adds tracing to all requests."""

    def __init__(self, service_name: str = SERVICE_NAME_VAL):
        self.service_name = service_name

    async def __call__(self, scope, receive, send):
        """ASGI middleware callable."""
        if scope["type"] != "http":
            return

        headers = dict(scope.get("headers", []))
        headers_dict = {k.decode(): v.decode() for k, v in headers}

        with tracer.span(f"{self.service_name}.request", headers=headers_dict) as span:
            span.set_attribute("http.method", scope.get("method", ""))
            span.set_attribute("http.url", scope.get("path", ""))

            await self._handle_request(scope, receive, send, span)

    async def _handle_request(self, scope, receive, send, span):
        """Handle the request with tracing."""
        from fastapi import Response

        async def tracing_receive():
            return await receive()

        async def tracing_send(message):
            if message["type"] == "http.response.start":
                span.set_attribute("http.status_code", message.get("status", 500))
            await send(message)

        from fastapi import Request
        request = Request(scope, tracing_receive)

        try:
            response = await self._call_app(request)
            await tracing_send({
                "type": "http.response.start",
                "status": response.status_code,
                "headers": response.headers.items(),
            })
            body = response.body
            await tracing_send({
                "type": "http.response.body",
                "body": body,
            })
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise

    async def _call_app(self, request: Request):
        """Call the next middleware or endpoint."""
        from fastapi.applications import FastAPI
        handler = request.app.middleware_stack
        return await handler(request)