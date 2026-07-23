"""
KV caching module for IronSilo.

Provides cross-session caching for LLM responses with
LRU eviction, TTL support, and persistence to disk.

Sub-modules:
  - models.py  -> CacheEntry, CacheStats
  - lru.py     -> LRUCache
  - keys.py    -> CacheKeyBuilder
  - kv.py      -> KVCache, create_kv_cache
"""

from .keys import CacheKeyBuilder
from .kv import KVCache, create_kv_cache
from .lru import LRUCache
from .models import CacheEntry, CacheStats

__version__ = "1.1.0"

__all__ = [
    "CacheEntry",
    "CacheKeyBuilder",
    "CacheStats",
    "KVCache",
    "LRUCache",
    "create_kv_cache",
]
