"""
Cross-session KV caching for LLM responses.
[Backward-compatible re-export module]

This module has been split into sub-modules within the cache/ package:
  - cache/models.py  -> CacheEntry, CacheStats
  - cache/lru.py     -> LRUCache
  - cache/keys.py    -> CacheKeyBuilder
  - cache/kv.py      -> KVCache, create_kv_cache

All symbols are re-exported here for backward compatibility.
New code should import directly from the sub-modules above.
"""

from .lru import LRUCache
from .keys import CacheKeyBuilder
from .kv import KVCache, create_kv_cache
from .models import CacheEntry, CacheStats

__all__ = [
    "CacheEntry",
    "CacheKeyBuilder",
    "CacheStats",
    "KVCache",
    "LRUCache",
    "create_kv_cache",
]
