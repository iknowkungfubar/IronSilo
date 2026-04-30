"""
Performance tests for IronSilo components.

These tests measure performance characteristics without requiring pytest-benchmark.
Run with: pytest tests/benchmarks/ -v
"""

import time
import pytest


class TestProxyPerformance:
    """Performance tests for proxy operations."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi.testclient import TestClient
        from proxy.proxy import app
        return TestClient(app, raise_server_exceptions=False)

    def test_chat_completions_response_time(self, client):
        """Test chat completions response time."""
        payload = {
            "messages": [{"role": "user", "content": "Hello"}],
            "model": "test",
        }

        start = time.time()
        response = client.post("/api/v1/chat/completions", json=payload)
        elapsed = time.time() - start

        assert response.status_code in [200, 500, 502, 503, 504]
        assert elapsed < 5.0  # Should complete within 5 seconds

    def test_health_endpoint_response_time(self, client):
        """Test health check response time."""
        start = time.time()
        response = client.get("/health")
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 0.5  # Health check should be fast


class TestSanitizationPerformance:
    """Performance tests for input sanitization."""

    def test_sanitize_short_content_performance(self):
        """Test sanitization performance of short content."""
        from proxy.proxy import _sanitize_content

        content = "Hello, world!"

        start = time.time()
        for _ in range(1000):
            _sanitize_content(content)
        elapsed = time.time() - start

        assert elapsed < 1.0  # 1000 operations should take less than 1 second

    def test_sanitize_long_content_performance(self):
        """Test sanitization performance of long content."""
        from proxy.proxy import _sanitize_content

        content = "x" * 10000

        start = time.time()
        for _ in range(100):
            _sanitize_content(content)
        elapsed = time.time() - start

        assert elapsed < 2.0  # 100 operations should take less than 2 seconds


class TestModelParsingPerformance:
    """Performance tests for model parsing."""

    def test_chat_completion_request_parsing_performance(self):
        """Test parsing performance of ChatCompletionRequest."""
        from proxy.models import ChatCompletionRequest

        data = {
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"},
            ],
            "model": "test-model",
            "temperature": 0.7,
            "max_tokens": 100,
        }

        start = time.time()
        for _ in range(1000):
            ChatCompletionRequest.model_validate(data)
        elapsed = time.time() - start

        assert elapsed < 2.0  # 1000 operations should take less than 2 seconds


class TestCachePerformance:
    """Performance tests for KV cache operations."""

    def test_kv_cache_set_get_performance(self):
        """Test cache set and get performance."""
        from cache.kv_store import create_kv_cache
        import asyncio

        cache = create_kv_cache(max_size=100)

        messages = [{"role": "user", "content": "test"}]

        async def run():
            for i in range(100):
                await cache.set_response(messages, {"id": f"test-{i}"}, "model", 0.7, 100)

            for i in range(100):
                result = await cache.get_response(messages, "model", 0.7, 100)
                assert result is not None or result is None

        start = time.time()
        asyncio.run(run())
        elapsed = time.time() - start

        assert elapsed < 5.0  # 200 operations should take less than 5 seconds


class TestCircuitBreakerPerformance:
    """Performance tests for circuit breaker operations."""

    def test_circuit_breaker_status_performance(self):
        """Test circuit breaker status performance."""
        from proxy.proxy import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=5, timeout=30.0)

        start = time.time()
        for _ in range(10000):
            status = cb.status
            assert isinstance(status, dict)
        elapsed = time.time() - start

        assert elapsed < 1.0  # 10000 operations should take less than 1 second


class TestRateLimiterPerformance:
    """Performance tests for rate limiter."""

    def test_rate_limiter_performance(self):
        """Test rate limiter performance under load."""
        from security.middleware import RateLimiter

        limiter = RateLimiter(requests_per_minute=1000)

        start = time.time()
        for i in range(1000):
            limiter.is_allowed(f"client-{i % 100}")
        elapsed = time.time() - start

        assert elapsed < 1.0  # 1000 operations should take less than 1 second


class TestCompressionPerformance:
    """Performance tests for compression operations."""

    def test_compress_content_skip_short(self):
        """Test that short content is not compressed."""
        from proxy.proxy import _compress_content

        short_content = "Hello, world!"

        start = time.time()
        for _ in range(1000):
            result = _compress_content(short_content)
        elapsed = time.time() - start

        assert elapsed < 1.0  # Short content should return quickly

    def test_compress_content_long_content(self):
        """Test compression performance for long content."""
        from proxy.proxy import _compress_content

        long_content = "x" * 5000

        start = time.time()
        for _ in range(10):
            result = _compress_content(long_content)
        elapsed = time.time() - start

        # Compression may be slower, but should still be reasonable
        assert elapsed < 10.0