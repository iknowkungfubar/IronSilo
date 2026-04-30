"""
Pytest configuration for load tests.

Provides fixtures and helpers for load testing the proxy.
"""

import pytest


def pytest_addoption(parser):
    """Add custom command line options for load tests."""
    parser.addoption(
        "--target-host",
        action="store",
        default="http://localhost:8080",
        help="Target host for load tests",
    )
    parser.addoption(
        "--users",
        action="store",
        default="10",
        help="Number of concurrent users",
    )
    parser.addoption(
        "--spawn-rate",
        action="store",
        default="5",
        help="User spawn rate",
    )
    parser.addoption(
        "--run-time",
        action="store",
        default="30s",
        help="Test run time (e.g., 30s, 1m, 5m)",
    )


@pytest.fixture
def target_host(request):
    """Get target host from command line or default."""
    return request.config.getoption("--target-host")
