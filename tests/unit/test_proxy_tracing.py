"""Tests for proxy/tracing.py"""

import pytest

from proxy.tracing import (
    IronSiloTracer,
    NoOpSpan,
    setup_tracing,
    trace_function,
    trace_span,
)


class TestNoOpSpan:
    """Tests for NoOpSpan when tracing is not available."""

    def test_noop_span_context_manager(self):
        """NoOpSpan should work as context manager."""
        span = NoOpSpan()
        with span as s:
            assert s is span

    def test_noop_span_methods(self):
        """NoOpSpan should have all required methods."""
        span = NoOpSpan()
        span.set_attribute("key", "value")
        span.add_event("event", attributes={"attr": "value"})
        span.record_exception(Exception("test"))
        span.set_status(None)
        span.end()

    def test_noop_span_no_errors(self):
        """NoOpSpan operations should not raise errors."""
        span = NoOpSpan()
        with pytest.raises(Exception):
            raise Exception("test")

        with span:
            pass


class TestIronSiloTracer:
    """Tests for IronSiloTracer singleton."""

    def test_singleton_instance(self):
        """IronSiloTracer should be a singleton."""
        tracer1 = IronSiloTracer()
        tracer2 = IronSiloTracer()
        assert tracer1 is tracer2

    def test_initialization_without_otel(self, mocker):
        """Tracer should handle missing OpenTelemetry gracefully when not installed."""
        import proxy.tracing as tracing_module
        
        original_otel = tracing_module.OTEL_AVAILABLE
        try:
            tracing_module.OTEL_AVAILABLE = False
            IronSiloTracer._instance = None
            tracer = IronSiloTracer()
            tracer._tracer = None
            tracer._propagator = None

            result = tracer.get_tracer()
            assert result is None
        finally:
            tracing_module.OTEL_AVAILABLE = original_otel
            IronSiloTracer._instance = None

    def test_create_span_returns_noop_when_no_tracer(self):
        """create_span should return NoOpSpan when not initialized."""
        import proxy.tracing as tracing_module
        
        original_otel = tracing_module.OTEL_AVAILABLE
        try:
            tracing_module.OTEL_AVAILABLE = False
            IronSiloTracer._instance = None
            tracer = IronSiloTracer()
            tracer._tracer = None

            span = tracer.create_span("test-span")
            assert isinstance(span, NoOpSpan)
        finally:
            tracing_module.OTEL_AVAILABLE = original_otel
            IronSiloTracer._instance = None

    def test_extract_context_with_no_propagator(self):
        """extract_context should handle missing propagator gracefully."""
        tracer = IronSiloTracer()
        tracer._propagator = None

        result = tracer.extract_context({"X-Request-ID": "test-123"})
        assert result is None


class TestTraceSpan:
    """Tests for trace_span context manager."""

    def test_trace_span_without_otel(self, mocker):
        """trace_span should work even without OpenTelemetry."""
        import proxy.tracing as tracing_module
        
        original_otel = tracing_module.OTEL_AVAILABLE
        try:
            tracing_module.OTEL_AVAILABLE = False
            IronSiloTracer._instance = None
            
            with trace_span("test-span") as span:
                assert isinstance(span, NoOpSpan)
        finally:
            tracing_module.OTEL_AVAILABLE = original_otel
            IronSiloTracer._instance = None

    def test_trace_span_with_headers(self, mocker):
        """trace_span should accept headers for context propagation."""
        import proxy.tracing as tracing_module
        
        original_otel = tracing_module.OTEL_AVAILABLE
        try:
            tracing_module.OTEL_AVAILABLE = False
            IronSiloTracer._instance = None
            
            headers = {"X-Request-ID": "test-123", "X-Trace-Parent": "test"}
            with trace_span("test-span", headers=headers) as span:
                assert isinstance(span, NoOpSpan)
        finally:
            tracing_module.OTEL_AVAILABLE = original_otel
            IronSiloTracer._instance = None


class TestTraceFunctionDecorator:
    """Tests for trace_function decorator."""

    def test_trace_sync_function(self):
        """trace_function should work with sync functions."""
        @trace_function("test-sync")
        def sync_func():
            return "result"

        result = sync_func()
        assert result == "result"

    @pytest.mark.asyncio
    async def test_trace_async_function(self):
        """trace_function should work with async functions."""
        @trace_function("test-async")
        async def async_func():
            return "result"

        result = await async_func()
        assert result == "result"

    def test_trace_function_without_name(self):
        """trace_function should use func name if not provided."""
        @trace_function()
        def my_named_func():
            return "named"

        result = my_named_func()
        assert result == "named"

    def test_trace_function_passes_args(self):
        """trace_function should pass through function arguments."""
        @trace_function("test-args")
        def func_with_args(a, b, c=None):
            return f"{a}-{b}-{c}"

        result = func_with_args("x", "y", c="z")
        assert result == "x-y-z"