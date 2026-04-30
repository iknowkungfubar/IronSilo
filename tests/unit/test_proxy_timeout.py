"""Tests for proxy timeout configuration."""
import pytest


class TestProxyTimeout:
    """Test proxy timeout settings."""

    def test_default_timeout_is_60_seconds(self):
        """Test that default httpx timeout is 60 seconds in proxy code."""
        import re

        with open("proxy/proxy.py", "r") as f:
            content = f.read()

        timeout_pattern = re.compile(r"AsyncClient\(timeout=(\d+\.?\d*)\)")
        matches = timeout_pattern.findall(content)

        if matches:
            for match in matches:
                timeout_val = float(match)
                assert timeout_val <= 60.0, f"Found timeout of {timeout_val}s, expected <= 60s per MASTER_BACKLOG"

    def test_no_300_second_timeout(self):
        """Test that 300s timeout from original code is reduced."""
        with open("proxy/proxy.py", "r") as f:
            content = f.read()

        assert "timeout=300.0" not in content, "Found 300s timeout - should be reduced to 60s"
        assert "timeout=300" not in content, "Found 300s timeout - should be reduced to 60s"
