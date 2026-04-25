"""
Cross-session KV caching for LLM responses.

This module provides in-memory caching with LRU eviction and
persistence to disk for surviving container restarts.

SECURITY: Uses JSON serialization instead of pickle to prevent
arbitrary code execution vulnerabilities.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

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


class LRUCache:
    """
    Thread-safe LRU cache with TTL support.
    
    Features:
    - LRU eviction policy
    - TTL (time-to-live) support
    - Size limits
    - Thread-safe operations
    - Statistics tracking
    - JSON persistence to disk (safe from code injection)
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        max_bytes: int = 100 * 1024 * 1024,  # 100MB
        default_ttl: int = 3600,
        persist_path: Optional[Path] = None,
    ):
        """
        Initialize LRU cache.
        
        Args:
            max_size: Maximum number of entries
            max_bytes: Maximum total size in bytes
            default_ttl: Default TTL in seconds
            persist_path: Optional path for persistence
        """
        self.max_size = max_size
        self.max_bytes = max_bytes
        self.default_ttl = default_ttl
        self.persist_path = persist_path
        
        # Cache storage (OrderedDict for LRU)
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        
        # Statistics
        self._stats = CacheStats()
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
        
        # Load persisted cache if exists
        if persist_path and persist_path.exists():
            self._load_from_disk()
        
        logger.info(
            "LRU cache initialized",
            max_size=max_size,
            max_bytes_mb=max_bytes / (1024 * 1024),
            default_ttl=default_ttl,
        )
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        async with self._lock:
            if key not in self._cache:
                self._stats.misses += 1
                return None
            
            entry = self._cache[key]
            
            # Check if expired
            if entry.is_expired:
                del self._cache[key]
                self._stats.size_bytes -= entry.size_bytes
                self._stats.entry_count -= 1
                self._stats.misses += 1
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            
            # Update entry
            entry.touch()
            
            # Update stats
            self._stats.hits += 1
            
            return entry.value
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> None:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL override
        """
        async with self._lock:
            # Calculate size
            size_bytes = self._calculate_size(value)
            
            # Check if we need to evict
            await self._evict_if_needed(size_bytes)
            
            # Create entry
            entry = CacheEntry(
                key=key,
                value=value,
                size_bytes=size_bytes,
                ttl_seconds=ttl or self.default_ttl,
            )
            
            # Track if this is a new key
            is_new_key = key not in self._cache
            
            # If key exists, remove old size
            if not is_new_key:
                old_entry = self._cache[key]
                self._stats.size_bytes -= old_entry.size_bytes
                del self._cache[key]
            
            # Add new entry
            self._cache[key] = entry
            self._stats.size_bytes += size_bytes
            
            # Only increment entry count for new keys
            if is_new_key:
                self._stats.entry_count += 1
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
    
    async def delete(self, key: str) -> bool:
        """
        Delete entry from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if entry was deleted
        """
        async with self._lock:
            if key not in self._cache:
                return False
            
            entry = self._cache[key]
            del self._cache[key]
            
            self._stats.size_bytes -= entry.size_bytes
            self._stats.entry_count -= 1
            
            return True
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
            self._stats = CacheStats()
    
    async def _evict_if_needed(self, new_entry_size: int) -> None:
        """Evict entries if cache is full."""
        # Check size limits
        while (
            len(self._cache) >= self.max_size or
            self._stats.size_bytes + new_entry_size > self.max_bytes
        ):
            if not self._cache:
                break
            
            # Remove least recently used (first item)
            key, entry = self._cache.popitem(last=False)
            
            self._stats.size_bytes -= entry.size_bytes
            self._stats.entry_count -= 1
            self._stats.evictions += 1
            
            logger.debug(
                "Evicted cache entry",
                key=key,
                reason="size_limit",
            )
    
    def _calculate_size(self, value: Any) -> int:
        """
        Calculate approximate size of value in bytes.
        
        Uses JSON serialization for safety.
        """
        try:
            if isinstance(value, str):
                return len(value.encode('utf-8'))
            elif isinstance(value, (int, float, bool)):
                return len(str(value))
            elif isinstance(value, (list, tuple)):
                return sum(self._calculate_size(item) for item in value)
            elif isinstance(value, dict):
                return sum(
                    self._calculate_size(k) + self._calculate_size(v)
                    for k, v in value.items()
                )
            elif isinstance(value, bytes):
                return len(value)
            else:
                # For complex objects, try JSON serialization
                try:
                    return len(json.dumps(value, default=str).encode('utf-8'))
                except (TypeError, ValueError):
                    # Fallback estimate
                    return 1024
        except Exception:
            # Fallback estimate
            return 1024
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        return self._stats.model_copy()
    
    async def persist(self) -> None:
        """
        Persist cache to disk using JSON.
        
        SECURITY: Uses JSON instead of pickle to prevent
        arbitrary code execution if cache file is tampered with.
        """
        if not self.persist_path:
            return
        
        async with self._lock:
            try:
                data = {
                    "version": 2,  # Version for future compatibility
                    "entries": {
                        key: {
                            "key": entry.key,
                            "value": entry.value,
                            "created_at": entry.created_at,
                            "accessed_at": entry.accessed_at,
                            "access_count": entry.access_count,
                            "size_bytes": entry.size_bytes,
                            "ttl_seconds": entry.ttl_seconds,
                        }
                        for key, entry in self._cache.items()
                        if not entry.is_expired
                    },
                    "stats": self._stats.model_dump(),
                }
                
                # Ensure directory exists
                self.persist_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write to file as JSON (safe from code injection)
                with open(self.persist_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, default=str)
                
                logger.info(
                    "Cache persisted to disk (JSON)",
                    path=str(self.persist_path),
                    entries=len(data["entries"]),
                )
                
            except Exception as e:
                logger.error("Failed to persist cache", error=str(e))
    
    def _load_from_disk(self) -> None:
        """
        Load cache from disk.
        
        SECURITY: Uses JSON instead of pickle to prevent
        arbitrary code execution from tampered cache files.
        """
        try:
            # Try JSON first (new format)
            if self.persist_path.suffix == '.json':
                with open(self.persist_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                # Try to read as JSON even without .json extension
                with open(self.persist_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            # Restore entries
            for key, entry_data in data.get("entries", {}).items():
                entry = CacheEntry(**entry_data)
                
                # Skip expired entries
                if not entry.is_expired:
                    self._cache[key] = entry
                    self._stats.size_bytes += entry.size_bytes
                    self._stats.entry_count += 1
            
            # Restore stats
            if "stats" in data:
                self._stats = CacheStats(**data["stats"])
            
            logger.info(
                "Cache loaded from disk (JSON)",
                path=str(self.persist_path),
                entries=len(self._cache),
            )
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning("Failed to load cache from disk (invalid format)", error=str(e))
        except FileNotFoundError:
            logger.debug("No existing cache file found")
        except Exception as e:
            logger.warning("Failed to load cache from disk", error=str(e))


class CacheKeyBuilder:
    """Builds cache keys for LLM requests."""
    
    @staticmethod
    def build_messages_key(
        messages: List[Dict[str, str]],
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """
        Build cache key from messages.
        
        Args:
            messages: Chat messages
            model: Model name
            temperature: Temperature setting
            max_tokens: Max tokens setting
            
        Returns:
            Cache key string
        """
        # Normalize messages
        normalized = []
        for msg in messages:
            normalized.append({
                "role": msg.get("role", ""),
                "content": msg.get("content", ""),
            })
        
        # Create key components
        key_data = {
            "messages": normalized,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        # Hash the key
        key_json = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_json.encode()).hexdigest()


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
        key = self.key_builder.build_messages_key(
            messages, model, temperature, max_tokens
        )
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
        key = self.key_builder.build_messages_key(
            messages, model, temperature, max_tokens
        )
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
        key = self.key_builder.build_messages_key(
            messages, model, temperature, max_tokens
        )
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
        KVCache instance
    """
    persist_path = None
    if persist_dir:
        # Use .json extension for safe JSON persistence
        persist_path = persist_dir / "llm_cache.json"
    
    return KVCache(
        max_size=max_size,
        persist_path=persist_path,
    )
