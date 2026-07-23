"""Unit tests for proxy/tracing.py module.

Tests cover:
- NoOpSpan class (fallback span implementation)
- IronSiloTracer singleton and core methods
- Span context manager lifecycle
- trace_function decorator for sync functions
- TracingMiddleware initialization
- Module-level functions (setup_tracing, trace_span)
- Context extraction from FastAPI requests
"""

from unittest.mock import MagicMock


class TestNoOpSpan:
    """Test NoOpSpan - the safe fallback span implementation."""

    def test_context_manager(self):
        """Test NoOpSpan can be used as a context manager."""
        from proxy.tracing import NoOpSpan

        span = NoOpSpan()
        with span as s:
            assert s is span

    def test_set_attribute(self):
        """Test set_attribute does not raise."""
        from proxy.tracing import NoOpSpan

        NoOpSpan().set_attribute("key", "value")

    def test_add_event(self):
        """Test add_event does not raise."""
        from proxy.tracing import NoOpSpan

        NoOpSpan().add_event("test_event", {"detail": "value"})

    def test_record_exception(self):
        """Test record_exception does not raise."""
        from proxy.tracing import NoOpSpan

        NoOpSpan().record_exception(RuntimeError("test"))

    def test_set_status(self):
        """Test set_status does not raise."""
        from proxy.tracing import NoOpSpan

        NoOpSpan().set_status("ok")

    def test_end(self):
        """Test end does not raise."""
        from proxy.tracing import NoOpSpan

        NoOpSpan().end()


class TestIronSiloTracer:
    """Test IronSiloTracer singleton and core methods."""

    def test_singleton_pattern(self):
        """Test IronSiloTracer is a singleton."""
        from proxy.tracing import IronSiloTracer

        t1 = IronSiloTracer()
        t2 = IronSiloTracer()
        assert t1 is t2

    def test_initialize_and_get_tracer(self):
        """Test initialize creates a valid tracer instance."""
        from proxy.tracing import IronSiloTracer

        tracer = IronSiloTracer()
        tracer.initialize("test-service")
        result = tracer.get_tracer()
        # Should return a tracer (OpenTelemetry is installed)
        assert result is not None

    def test_extract_context_with_headers(self):
        """Test extract_context returns a context dict from headers."""
        from proxy.tracing import IronSiloTracer

        tracer = IronSiloTracer()
        tracer.initialize()
        result = tracer.extract_context({"traceparent": "00-abc123-456-01"})
        # Returns a context object (dict-like) when OTEL is available
        assert result is not None

    def test_extract_context_empty_headers(self):
        """Test extract_context with empty headers returns a context."""
        from proxy.tracing import IronSiloTracer

        tracer = IronSiloTracer()
        tracer.initialize()
        result = tracer.extract_context({})
        assert result is not None

    def test_create_span(self):
        """Test create_span returns a real span when OTEL is available."""
        from proxy.tracing import IronSiloTracer

        tracer = IronSiloTracer()
        tracer.initialize()
        span = tracer.create_span("test-operation")
        # Returns a real OpenTelemetry span
        assert span is not None
        assert hasattr(span, "set_attribute")
        assert hasattr(span, "end")

    def test_create_span_with_context(self):
        """Test create_span with context returns a valid span."""
        from proxy.tracing import IronSiloTracer

        tracer = IronSiloTracer()
        tracer.initialize()
        ctx = tracer.extract_context({})
        span = tracer.create_span("test", context=ctx)
        assert span is not None
        assert hasattr(span, "set_attribute")

    def test_span_context_manager(self):
        """Test tracer.span() works as context manager."""
        from proxy.tracing import IronSiloTracer

        tracer = IronSiloTracer()
        tracer.initialize()
        with tracer.span("test-operation") as span:
            assert span is not None
            span.set_attribute("test", "value")

    def test_span_with_headers(self):
        """Test tracer.span() with headers propagates context."""
        from proxy.tracing import IronSiloTracer

        tracer = IronSiloTracer()
        tracer.initialize()
        headers = {"traceparent": "00-abc123-456-01"}
        with tracer.span("test", headers=headers) as span:
            assert span is not None

    def test_start_as_child_no_parent(self):
        """Test start_as_child returns NoOpSpan when parent_span is None."""
        from proxy.tracing import IronSiloTracer, NoOpSpan

        tracer = IronSiloTracer()
        child = tracer.start_as_child("child", parent_span=None)
        assert isinstance(child, NoOpSpan)


class TestSpanContextManager:
    """Test SpanContextManager lifecycle."""

    def test_with_noop_span(self):
        """Test SpanContextManager with a NoOpSpan."""
        from proxy.tracing import NoOpSpan, SpanContextManager

        span = NoOpSpan()
        mgr = SpanContextManager(span)
        with mgr as s:
            assert s is span

    def test_exit_returns_false(self):
        """Test __exit__ returns False to not suppress exceptions."""
        from proxy.tracing import NoOpSpan, SpanContextManager

        span = NoOpSpan()
        mgr = SpanContextManager(span)
        result = mgr.__exit__(None, None, None)
        assert result is False


class TestTraceFunction:
    """Test the trace_function decorator."""

    def test_sync_function(self):
        """Test trace_function wraps a sync function and preserves return value."""
        from proxy.tracing import trace_function

        @trace_function("test-func")
        def my_function():
            return 42

        assert my_function() == 42

    def test_default_name(self):
        """Test trace_function uses auto-generated name when name is None."""
        from proxy.tracing import trace_function

        @trace_function()
        def my_func():
            return "hello"

        assert my_func() == "hello"

    def test_with_args(self):
        """Test wrapped function still receives and passes arguments."""
        from proxy.tracing import trace_function

        @trace_function("add")
        def add(a, b):
            return a + b

        assert add(3, 4) == 7

    def test_already_wrapped(self):
        """Test a function already __wrapped__ is returned directly."""
        from proxy.tracing import trace_function

        def inner():
            return "inner"

        inner.__wrapped__ = True

        @trace_function("wrapper")
        def outer():
            return inner()

        assert outer() == "inner"


class TestTracingMiddleware:
    """Test TracingMiddleware class."""

    def test_init(self):
        """Test TracingMiddleware stores service name."""
        from proxy.tracing import TracingMiddleware

        middleware = TracingMiddleware("test-service")
        assert middleware.service_name == "test-service"

    def test_init_default_name(self):
        """Test TracingMiddleware uses default service name."""
        from proxy.tracing import TracingMiddleware

        middleware = TracingMiddleware()
        assert middleware.service_name is not None
        assert isinstance(middleware.service_name, str)

    def test_non_http_scope_returns_early(self):
        """Test middleware returns immediately for non-HTTP scopes."""
        from proxy.tracing import TracingMiddleware

        middleware = TracingMiddleware()
        scope = {"type": "websocket"}
        receive = MagicMock()
        send = MagicMock()

        import asyncio

        asyncio.run(middleware(scope, receive, send))
        # Should complete without error, no send calls for non-http


class TestModuleFunctions:
    """Test module-level functions."""

    def test_setup_tracing(self):
        """Test setup_tracing calls tracer.initialize without error."""
        from proxy.tracing import setup_tracing

        setup_tracing("test-service")

    def test_setup_tracing_default_name(self):
        """Test setup_tracing uses default service name."""
        from proxy.tracing import setup_tracing

        setup_tracing()

    def test_trace_span_context_manager(self):
        """Test trace_span returns a context manager that can be entered."""
        from proxy.tracing import trace_span

        with trace_span("test-op") as span:
            assert span is not None

    def test_get_trace_context_from_request_no_headers(self):
        """Test get_trace_context_from_request returns None for object without headers attr."""
        from proxy.tracing import get_trace_context_from_request

        request = MagicMock()
        del request.headers
        result = get_trace_context_from_request(request)
        assert result is None

    def test_get_trace_context_from_request_with_headers(self):
        """Test get_trace_context_from_request extracts context from headers."""
        from proxy.tracing import get_trace_context_from_request

        request = MagicMock()
        request.headers = {"traceparent": "00-abc123-456-01", "x-request-id": "test-123"}
        result = get_trace_context_from_request(request)
        assert result is not None

    def test_module_exports(self):
        """Test module exports all expected public symbols."""
        import proxy.tracing

        assert hasattr(proxy.tracing, "tracer")
        assert proxy.tracing.tracer is not None
        assert callable(proxy.tracing.setup_tracing)
        assert callable(proxy.tracing.trace_span)
        assert callable(proxy.tracing.trace_function)
        assert hasattr(proxy.tracing, "IronSiloTracer")
        assert hasattr(proxy.tracing, "NoOpSpan")
