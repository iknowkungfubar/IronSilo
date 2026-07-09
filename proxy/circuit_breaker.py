"""Circuit breaker for upstream LLM requests.

Extracted from proxy.py for independent testability.
"""

from __future__ import annotations

import time
import logging
from typing import Any

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Circuit breaker pattern for upstream LLM requests.

    Prevents cascading failures by opening the circuit when failures
    exceed the threshold. After a timeout, allows a single test request
    (half-open) to check if the upstream has recovered.
    """

    def __init__(self, failure_threshold: int = 5, timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.state = "closed"

    async def can_proceed(self) -> bool:
        """Check if the circuit allows requests to proceed."""
        if self.state == "closed":
            return True

        if self.state == "open":
            if self.last_failure_time and (time.time() - self.last_failure_time) > self.timeout:
                self.state = "half-open"
                logger.info("Circuit breaker transitioning to half-open")
                return True
            logger.warning("Circuit breaker is OPEN — request blocked")
            return False

        if self.state == "half-open":
            return True

        return True

    async def record_success(self) -> None:
        """Record a successful request, potentially closing the circuit."""
        if self.state == "half-open":
            logger.info("Circuit breaker closing — upstream recovered")
        self.state = "closed"
        self.failure_count = 0
        self.last_failure_time = None

    async def record_failure(self) -> None:
        """Record a failed request, potentially opening the circuit."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.error(
                "Circuit breaker OPEN after %d failures. Blocking for %.1fs",
                self.failure_count,
                self.timeout,
            )

    def status(self) -> dict[str, Any]:
        """Return current circuit breaker status."""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "timeout": self.timeout,
        }
