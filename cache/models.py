"""Pydantic data models for the cache system.

Provides CacheEntry and CacheStats models used across
the LRU cache, KV cache store, and persistence layer.
"""

from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel, Field

import structlog

logger = structlog.get_logger(__name__)


class CacheEntry(BaseModel):
    """Entry in the cache."""

    key: str
    value: Any
    created_at: float = Field(default_factory=time.time)
    accessed_at: float = Field(default_factory=time.time)
    access_count: int = 0
    size_bytes: int = 0
    ttl_seconds: int = 3600

    @property
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.ttl_seconds <= 0:
            return False
        return time.time() - self.created_at > self.ttl_seconds

    def touch(self) -> None:
        """Update access time and count."""
        self.accessed_at = time.time()
        self.access_count += 1


class CacheStats(BaseModel):
    """Cache statistics."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size_bytes: int = 0
    entry_count: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate."""
        return 1.0 - self.hit_rate


__all__ = [
    "CacheEntry",
    "CacheStats",
]
