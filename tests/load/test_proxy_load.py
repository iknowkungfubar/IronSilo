"""
Load tests for the LLMLingua Proxy.

Tests cover:
- Concurrent request handling
- Response time under load
- Error rate under load
- Retry behavior under load

This file is a placeholder for load tests.
Load tests require locust to be installed separately and are typically
run using the locust CLI, not pytest:

    pip install locust
    locust -f tests/load/test_proxy_load.py --headless -u 100 -r 10 --run-time 30s --host http://localhost:8080

The actual load test implementations are in the locustfile.py for manual execution.
"""

import pytest


@pytest.mark.skip(reason="Load tests require locust CLI, not pytest. Run: locust -f tests/load/locustfile.py")
class TestLoadTestsPlaceholder:
    """Placeholder to prevent collection errors."""

    def test_load_tests_available(self):
        """Verify load test framework is available."""
        import importlib.util
        spec = importlib.util.find_spec("locust")
        assert spec is not None, "locust not installed (pip install locust)"
