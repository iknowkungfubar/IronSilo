"""Unit tests for proxy/circuit_breaker.py.

Tests the CircuitBreaker state machine:
- Closed (normal operation)
- Open (failures exceed threshold)
- Half-open (timeout elapsed, test request allowed)
"""

import time
from unittest.mock import patch

import pytest

from proxy.circuit_breaker import CircuitBreaker


class TestCircuitBreakerInitialState:
    """Circuit starts in closed state with zero failures."""

    def test_initial_state_is_closed(self):
        """Circuit breaker starts in closed state."""
        cb = CircuitBreaker()
        assert cb.state == "closed"
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_can_proceed_when_closed(self):
        """Closed circuit allows requests."""
        cb = CircuitBreaker()
        result = await cb.can_proceed()
        assert result is True

    def test_status_returns_config(self):
        """Status dict reflects current state and config."""
        cb = CircuitBreaker(failure_threshold=3, timeout=15.0)
        status = cb.status()
        assert status["state"] == "closed"
        assert status["failure_count"] == 0
        assert status["failure_threshold"] == 3
        assert status["timeout"] == 15.0


class TestCircuitBreakerFailureTracking:
    """Failure tracking and circuit-opening behavior."""

    @pytest.mark.asyncio
    async def test_record_failure_increments_count(self):
        """Each record_failure call increments the counter."""
        cb = CircuitBreaker(failure_threshold=5)
        await cb.record_failure()
        assert cb.failure_count == 1
        assert cb.state == "closed"

    @pytest.mark.asyncio
    async def test_record_failure_opens_at_threshold(self):
        """Circuit opens when failures reach the threshold."""
        cb = CircuitBreaker(failure_threshold=3)
        await cb.record_failure()
        await cb.record_failure()
        assert cb.state == "closed"
        await cb.record_failure()
        assert cb.state == "open"
        assert cb.failure_count == 3

    @pytest.mark.asyncio
    async def test_record_failure_records_timestamp(self):
        """record_failure sets last_failure_time."""
        cb = CircuitBreaker()
        await cb.record_failure()
        assert cb.last_failure_time is not None
        assert isinstance(cb.last_failure_time, float)

    @pytest.mark.asyncio
    async def test_can_proceed_blocks_when_open(self):
        """Open circuit blocks requests before timeout elapses."""
        cb = CircuitBreaker(failure_threshold=1, timeout=3600)
        await cb.record_failure()
        assert cb.state == "open"
        result = await cb.can_proceed()
        assert result is False
        assert cb.state == "open"


class TestCircuitBreakerStateTransitions:
    """State machine transitions between closed, open, and half-open."""

    @pytest.mark.asyncio
    async def test_open_transitions_to_half_open_after_timeout(self):
        """After timeout elapses, open circuit transitions to half-open and allows request."""
        cb = CircuitBreaker(failure_threshold=1, timeout=0)
        await cb.record_failure()
        assert cb.state == "open"
        result = await cb.can_proceed()
        assert result is True
        assert cb.state == "half-open"

    @pytest.mark.asyncio
    async def test_half_open_allows_requests(self):
        """Half-open circuit allows requests through."""
        cb = CircuitBreaker(failure_threshold=1, timeout=0)
        await cb.record_failure()
        await cb.can_proceed()
        assert cb.state == "half-open"
        result = await cb.can_proceed()
        assert result is True

    @pytest.mark.asyncio
    async def test_record_success_closes_from_half_open(self):
        """Successful request from half-open closes the circuit."""
        cb = CircuitBreaker(failure_threshold=1, timeout=0)
        await cb.record_failure()
        await cb.can_proceed()
        assert cb.state == "half-open"
        await cb.record_success()
        assert cb.state == "closed"
        assert cb.failure_count == 0
        assert cb.last_failure_time is None

    @pytest.mark.asyncio
    async def test_record_success_from_closed_stays_closed(self):
        """record_success on a closed circuit keeps it closed."""
        cb = CircuitBreaker()
        await cb.record_success()
        assert cb.state == "closed"

    @pytest.mark.asyncio
    async def test_record_failure_from_half_open_reopens(self):
        """Failed request from half-open re-opens the circuit."""
        cb = CircuitBreaker(failure_threshold=1, timeout=0)
        await cb.record_failure()
        await cb.can_proceed()
        assert cb.state == "half-open"
        await cb.record_failure()
        assert cb.state == "open"
        assert cb.failure_count == 2

    @pytest.mark.asyncio
    async def test_record_failure_keeps_timestamp(self):
        """record_failure updates last_failure_time each time."""
        cb = CircuitBreaker(failure_threshold=3)
        await cb.record_failure()
        t1 = cb.last_failure_time
        assert t1 is not None
        await cb.record_failure()
        t2 = cb.last_failure_time
        assert t2 is not None
        assert t2 >= t1


class TestCircuitBreakerEdgeCases:
    """Edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_can_proceed_unknown_state_defaults_true(self):
        """Unknown state defaults to allowing requests."""
        cb = CircuitBreaker()
        cb.state = "unknown"
        result = await cb.can_proceed()
        assert result is True

    def test_default_parameters(self):
        """Default failure_threshold is 5 and timeout is 30."""
        cb = CircuitBreaker()
        assert cb.failure_threshold == 5
        assert cb.timeout == 30.0

    @pytest.mark.asyncio
    async def test_can_proceed_with_barely_open(self):
        """Test edge: state open but no last_failure_time (should not crash)."""
        cb = CircuitBreaker(failure_threshold=1)
        cb.state = "open"
        cb.last_failure_time = None
        result = await cb.can_proceed()
        assert result is False
        assert cb.state == "open"
