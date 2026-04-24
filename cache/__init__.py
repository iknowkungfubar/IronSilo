"""
KV caching module for IronSilo.

Provides cross-session caching for LLM responses with
LRU eviction, TTL support, and persistence to disk.
"""

from .kv_store import CacheEntry, CacheKeyBuilder, CacheStats, KVCache, LRUCache, create_kv_cache

__version__ = "1.0.0"

__all__ = [
    "CacheEntry",
    "CacheKeyBuilder",
    "CacheStats",
    "KVCache",
    "LRUCache",
    "create_kv_cache",
]
