"""High-level KV cache interface for LLM proxy.

Provides caching for LLM responses with automatic key generation
and background persistence.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from .keys import CacheKeyBuilder
from .lru import LRUCache

logger = structlog.get_logger(__name__)


class KVCache:
    """
    High-level KV cache interface for LLM proxy.

    Provides caching for LLM responses with automatic key generation.
    """

    def __init__(
        self,
        max_size: int = 1000,
        max_bytes: int = 100 * 1024 * 1024,
        default_ttl: int = 3600,
        persist_path: Optional[Path] = None,
    ):
        self.cache = LRUCache(
            max_size=max_size,
            max_bytes=max_bytes,
            default_ttl=default_ttl,
            persist_path=persist_path,
        )
        self.key_builder = CacheKeyBuilder()

        # Background persistence task
        self._persist_task: Optional[asyncio.Task] = None

    async def start(self, persist_interval: int = 300) -> None:
        """Start background persistence task."""
        if self._persist_task:
            return

        async def persist_loop():
            while True:
                await asyncio.sleep(persist_interval)
                await self.cache.persist()

        self._persist_task = asyncio.create_task(persist_loop())
        logger.info("Cache persistence started", interval=persist_interval)

    async def stop(self) -> None:
        """Stop background persistence and save cache."""
        if self._persist_task:
            self._persist_task.cancel()
            try:
                await self._persist_task
            except asyncio.CancelledError:
                pass

        await self.cache.persist()
        logger.info("Cache stopped and persisted")

    async def get_response(
        self,
        messages: List[Dict[str, str]],
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Optional[Any]:
        """
        Get cached LLM response.

        Args:
            messages: Chat messages
            model: Model name
            temperature: Temperature setting
            max_tokens: Max tokens setting

        Returns:
            Cached response or None
        """
        key = self.key_builder.build_messages_key(messages, model, temperature, max_tokens)
        return await self.cache.get(key)

    async def set_response(
        self,
        messages: List[Dict[str, str]],
        response: Any,
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        ttl: Optional[int] = None,
    ) -> None:
        """
        Cache LLM response.

        Args:
            messages: Chat messages
            response: LLM response to cache
            model: Model name
            temperature: Temperature setting
            max_tokens: Max tokens setting
            ttl: Optional TTL override
        """
        key = self.key_builder.build_messages_key(messages, model, temperature, max_tokens)
        await self.cache.set(key, response, ttl)

    async def invalidate(
        self,
        messages: List[Dict[str, str]],
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> bool:
        """
        Invalidate cached response.

        Args:
            messages: Chat messages
            model: Model name
            temperature: Temperature setting
            max_tokens: Max tokens setting

        Returns:
            True if entry was invalidated
        """
        key = self.key_builder.build_messages_key(messages, model, temperature, max_tokens)
        return await self.cache.delete(key)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = self.cache.get_stats()
        return {
            "hits": stats.hits,
            "misses": stats.misses,
            "hit_rate": round(stats.hit_rate, 4),
            "evictions": stats.evictions,
            "size_bytes": stats.size_bytes,
            "size_mb": round(stats.size_bytes / (1024 * 1024), 2),
            "entry_count": stats.entry_count,
            "max_size": self.cache.max_size,
            "max_bytes": self.cache.max_bytes,
        }


def create_kv_cache(
    persist_dir: Optional[Path] = None,
    max_size: int = 1000,
) -> KVCache:
    """
    Create a KV cache instance.

    Args:
        persist_dir: Directory for persistence
        max_size: Maximum cache size

    Returns:
        Configured KVCache instance
    """
    persist_path = None
    if persist_dir:
        persist_path = persist_dir / "llm_cache.json"

    return KVCache(
        max_size=max_size,
        persist_path=persist_path,
    )


__all__ = [
    "KVCache",
    "create_kv_cache",
]
