"""
Unit tests for cache/kv_store.py module.

Tests cover:
- CacheEntry functionality
- CacheStats calculations
- LRUCache operations (get, set, delete, clear)
- LRU eviction policy
- TTL expiration
- Size-based eviction
- Persistence (save/load)
- CacheKeyBuilder
- KVCache high-level interface
- Thread safety with async operations
"""

import asyncio
import pickle
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from cache.kv_store import (
    CacheEntry,
    CacheStats,
    CacheKeyBuilder,
    KVCache,
    LRUCache,
    create_kv_cache,
)


class TestCacheEntry:
    """Test CacheEntry model."""
    
    def test_cache_entry_creation(self):
        """Test creating a cache entry."""
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            size_bytes=100,
            ttl_seconds=60,
        )
        
        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.size_bytes == 100
        assert entry.ttl_seconds == 60
        assert entry.access_count == 0
        assert entry.created_at > 0
        assert entry.accessed_at > 0
    
    def test_cache_entry_is_expired_false(self):
        """Test is_expired returns False for non-expired entry."""
        entry = CacheEntry(
            key="test",
            value="value",
            ttl_seconds=3600,
        )
        
        assert entry.is_expired is False
    
    def test_cache_entry_is_expired_true(self):
        """Test is_expired returns True for expired entry."""
        entry = CacheEntry(
            key="test",
            value="value",
            created_at=time.time() - 4000,  # Created 4000 seconds ago
            ttl_seconds=3600,
        )
        
        assert entry.is_expired is True
    
    def test_cache_entry_no_ttl(self):
        """Test entry with TTL <= 0 never expires."""
        entry = CacheEntry(
            key="test",
            value="value",
            created_at=time.time() - 100000,
            ttl_seconds=0,  # 0 means no expiration
        )
        
        assert entry.is_expired is False
    
    def test_cache_entry_touch(self):
        """Test touch updates access time and count."""
        entry = CacheEntry(key="test", value="value")
        initial_count = entry.access_count
        initial_time = entry.accessed_at
        
        time.sleep(0.01)  # Small delay
        entry.touch()
        
        assert entry.access_count == initial_count + 1
        assert entry.accessed_at > initial_time


class TestCacheStats:
    """Test CacheStats model."""
    
    def test_cache_stats_defaults(self):
        """Test default stats values."""
        stats = CacheStats()
        
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.evictions == 0
        assert stats.size_bytes == 0
        assert stats.entry_count == 0
    
    def test_hit_rate_empty(self):
        """Test hit rate with no requests."""
        stats = CacheStats()
        
        assert stats.hit_rate == 0.0
    
    def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        stats = CacheStats(hits=70, misses=30)
        
        assert abs(stats.hit_rate - 0.7) < 0.0001
        assert abs(stats.miss_rate - 0.3) < 0.0001
    
    def test_hit_rate_all_hits(self):
        """Test hit rate with all hits."""
        stats = CacheStats(hits=100, misses=0)
        
        assert stats.hit_rate == 1.0
        assert stats.miss_rate == 0.0


class TestLRUCache:
    """Test LRUCache class."""
    
    @pytest.mark.asyncio
    async def test_cache_init(self):
        """Test cache initialization."""
        cache = LRUCache(max_size=100, max_bytes=1024, default_ttl=60)
        
        assert cache.max_size == 100
        assert cache.max_bytes == 1024
        assert cache.default_ttl == 60
        assert len(cache._cache) == 0
    
    @pytest.mark.asyncio
    async def test_get_missing_key(self):
        """Test getting a missing key."""
        cache = LRUCache()
        
        result = await cache.get("missing")
        
        assert result is None
        assert cache._stats.misses == 1
    
    @pytest.mark.asyncio
    async def test_set_and_get(self):
        """Test basic set and get operations."""
        cache = LRUCache()
        
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        
        assert result == "value1"
        assert cache._stats.hits == 1
        assert cache._stats.entry_count == 1
    
    @pytest.mark.asyncio
    async def test_get_expired_entry(self):
        """Test getting an expired entry."""
        cache = LRUCache(default_ttl=1)
        
        await cache.set("key1", "value1")
        time.sleep(1.1)  # Wait for expiration
        
        result = await cache.get("key1")
        
        assert result is None
        assert cache._stats.misses == 1
        assert cache._stats.entry_count == 0
    
    @pytest.mark.asyncio
    async def test_delete_existing(self):
        """Test deleting an existing entry."""
        cache = LRUCache()
        
        await cache.set("key1", "value1")
        result = await cache.delete("key1")
        
        assert result is True
        assert cache._stats.entry_count == 0
    
    @pytest.mark.asyncio
    async def test_delete_missing(self):
        """Test deleting a missing entry."""
        cache = LRUCache()
        
        result = await cache.delete("missing")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_clear(self):
        """Test clearing the cache."""
        cache = LRUCache()
        
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.clear()
        
        assert cache._stats.entry_count == 0
        assert cache._stats.hits == 0
        assert cache._stats.misses == 0
    
    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        """Test LRU eviction when max_size is reached."""
        cache = LRUCache(max_size=3)
        
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        
        # Access key1 to make it recently used
        await cache.get("key1")
        
        # Add new entry, should evict key2 (least recently used)
        await cache.set("key4", "value4")
        
        assert await cache.get("key1") == "value1"
        assert await cache.get("key2") is None  # Evicted
        assert await cache.get("key3") == "value3"
        assert await cache.get("key4") == "value4"
        assert cache._stats.evictions == 1
    
    @pytest.mark.asyncio
    async def test_size_eviction(self):
        """Test eviction based on size limit."""
        cache = LRUCache(max_size=100, max_bytes=50)
        
        await cache.set("key1", "a" * 20)
        await cache.set("key2", "b" * 20)
        
        # Adding this should trigger eviction
        await cache.set("key3", "c" * 20)
        
        # key1 should be evicted (LRU)
        assert await cache.get("key1") is None
        assert cache._stats.evictions > 0
    
    @pytest.mark.asyncio
    async def test_update_existing_key(self):
        """Test updating an existing key."""
        cache = LRUCache()
        
        await cache.set("key1", "value1")
        await cache.set("key1", "value2")
        
        result = await cache.get("key1")
        
        assert result == "value2"
        assert cache._stats.entry_count == 1
    
    @pytest.mark.asyncio
    async def test_custom_ttl(self):
        """Test setting custom TTL per entry."""
        cache = LRUCache(default_ttl=3600)
        
        await cache.set("key1", "value1", ttl=1)  # 1 second TTL
        
        assert await cache.get("key1") == "value1"
        time.sleep(1.1)
        assert await cache.get("key1") is None
    
    def test_calculate_size_string(self):
        """Test size calculation for strings."""
        cache = LRUCache()
        
        size = cache._calculate_size("hello")
        
        assert size == 5  # "hello" is 5 bytes in UTF-8
    
    def test_calculate_size_number(self):
        """Test size calculation for numbers."""
        cache = LRUCache()
        
        size = cache._calculate_size(12345)
        
        assert size == len("12345")
    
    def test_calculate_size_list(self):
        """Test size calculation for lists."""
        cache = LRUCache()
        
        size = cache._calculate_size(["a", "b", "c"])
        
        assert size > 0
    
    def test_calculate_size_dict(self):
        """Test size calculation for dicts."""
        cache = LRUCache()
        
        size = cache._calculate_size({"key": "value"})
        
        assert size > 0
    
    def test_get_stats(self):
        """Test getting cache statistics."""
        cache = LRUCache()
        cache._stats.hits = 10
        cache._stats.misses = 5
        
        stats = cache.get_stats()
        
        assert stats.hits == 10
        assert stats.misses == 5
        assert isinstance(stats, CacheStats)
    
    @pytest.mark.asyncio
    async def test_persistence(self):
        """Test cache persistence to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            persist_path = Path(tmpdir) / "cache.pkl"
            
            # Create and populate cache
            cache1 = LRUCache(persist_path=persist_path)
            await cache1.set("key1", "value1")
            await cache1.set("key2", {"nested": "data"})
            await cache1.persist()
            
            # Load from disk
            cache2 = LRUCache(persist_path=persist_path)
            
            assert await cache2.get("key1") == "value1"
            assert await cache2.get("key2") == {"nested": "data"}
    
    @pytest.mark.asyncio
    async def test_persistence_skips_expired(self):
        """Test that expired entries are not persisted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            persist_path = Path(tmpdir) / "cache.pkl"
            
            cache1 = LRUCache(persist_path=persist_path, default_ttl=1)
            await cache1.set("key1", "value1")
            
            time.sleep(1.1)
            await cache1.persist()
            
            cache2 = LRUCache(persist_path=persist_path)
            
            assert await cache2.get("key1") is None
    
    @pytest.mark.asyncio
    async def test_load_nonexistent_file(self):
        """Test loading from non-existent file."""
        cache = LRUCache(persist_path=Path("/nonexistent/cache.pkl"))
        
        # Should not raise, just log warning
        assert len(cache._cache) == 0


class TestCacheKeyBuilder:
    """Test CacheKeyBuilder class."""
    
    def test_build_messages_key_basic(self):
        """Test building cache key from messages."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        
        key = CacheKeyBuilder.build_messages_key(messages)
        
        assert isinstance(key, str)
        assert len(key) == 64  # SHA256 hex digest
    
    def test_build_messages_key_with_params(self):
        """Test building cache key with model parameters."""
        messages = [{"role": "user", "content": "Test"}]
        
        key1 = CacheKeyBuilder.build_messages_key(
            messages, model="gpt-4", temperature=0.7
        )
        key2 = CacheKeyBuilder.build_messages_key(
            messages, model="gpt-3.5", temperature=0.7
        )
        
        # Different models should produce different keys
        assert key1 != key2
    
    def test_build_messages_key_deterministic(self):
        """Test that same inputs produce same key."""
        messages = [{"role": "user", "content": "Test"}]
        
        key1 = CacheKeyBuilder.build_messages_key(messages)
        key2 = CacheKeyBuilder.build_messages_key(messages)
        
        assert key1 == key2
    
    def test_build_messages_key_order_independent(self):
        """Test that message order affects key."""
        messages1 = [
            {"role": "user", "content": "A"},
            {"role": "assistant", "content": "B"},
        ]
        messages2 = [
            {"role": "assistant", "content": "B"},
            {"role": "user", "content": "A"},
        ]
        
        key1 = CacheKeyBuilder.build_messages_key(messages1)
        key2 = CacheKeyBuilder.build_messages_key(messages2)
        
        # Different order should produce different keys
        assert key1 != key2


class TestKVCache:
    """Test KVCache high-level interface."""
    
    @pytest.mark.asyncio
    async def test_kv_cache_init(self):
        """Test KVCache initialization."""
        kv = KVCache(max_size=100, default_ttl=60)
        
        assert kv.cache.max_size == 100
        assert kv.cache.default_ttl == 60
    
    @pytest.mark.asyncio
    async def test_get_response_miss(self):
        """Test cache miss for LLM response."""
        kv = KVCache()
        
        messages = [{"role": "user", "content": "Hello"}]
        result = await kv.get_response(messages, model="gpt-4")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_set_and_get_response(self):
        """Test caching and retrieving LLM responses."""
        kv = KVCache()
        
        messages = [{"role": "user", "content": "Hello"}]
        response = {"choices": [{"message": {"content": "Hi!"}}]}
        
        await kv.set_response(messages, response, model="gpt-4")
        result = await kv.get_response(messages, model="gpt-4")
        
        assert result == response
    
    @pytest.mark.asyncio
    async def test_invalidate(self):
        """Test invalidating cached response."""
        kv = KVCache()
        
        messages = [{"role": "user", "content": "Hello"}]
        response = {"content": "Hi!"}
        
        await kv.set_response(messages, response)
        result = await kv.invalidate(messages)
        
        assert result is True
        assert await kv.get_response(messages) is None
    
    @pytest.mark.asyncio
    async def test_invalidate_missing(self):
        """Test invalidating non-existent response."""
        kv = KVCache()
        
        messages = [{"role": "user", "content": "Hello"}]
        result = await kv.invalidate(messages)
        
        assert result is False
    
    def test_get_stats(self):
        """Test getting KV cache statistics."""
        kv = KVCache(max_size=100, max_bytes=1024 * 1024)
        
        stats = kv.get_stats()
        
        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate" in stats
        assert "max_size" in stats
        assert stats["max_size"] == 100
    
    @pytest.mark.asyncio
    async def test_start_and_stop(self):
        """Test starting and stopping background persistence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            persist_path = Path(tmpdir) / "cache.pkl"
            kv = KVCache(persist_path=persist_path)
            
            await kv.start(persist_interval=1)
            assert kv._persist_task is not None
            
            await kv.set_response(
                [{"role": "user", "content": "Test"}],
                {"response": "data"}
            )
            
            await kv.stop()
            
            # Verify data was persisted
            assert persist_path.exists()


class TestCreateKVCache:
    """Test create_kv_cache factory function."""
    
    def test_create_kv_cache_no_persist(self):
        """Test creating cache without persistence."""
        cache = create_kv_cache()
        
        assert cache is not None
        assert cache.cache.persist_path is None
    
    def test_create_kv_cache_with_persist(self):
        """Test creating cache with persistence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = create_kv_cache(persist_dir=Path(tmpdir))
            
            assert cache is not None
            assert cache.cache.persist_path is not None
            assert cache.cache.persist_path.name == "llm_cache.json"
    
    def test_create_kv_cache_custom_size(self):
        """Test creating cache with custom max size."""
        cache = create_kv_cache(max_size=500)
        
        assert cache.cache.max_size == 500


class TestConcurrency:
    """Test concurrent access to cache."""
    
    @pytest.mark.asyncio
    async def test_concurrent_writes(self):
        """Test concurrent write operations."""
        cache = LRUCache(max_size=100)
        
        async def write_key(i: int):
            await cache.set(f"key{i}", f"value{i}")
        
        # Write 50 keys concurrently
        await asyncio.gather(*[write_key(i) for i in range(50)])
        
        assert cache._stats.entry_count == 50
    
    @pytest.mark.asyncio
    async def test_concurrent_read_write(self):
        """Test concurrent read and write operations."""
        cache = LRUCache(max_size=100)
        
        async def writer():
            for i in range(10):
                await cache.set(f"key{i}", f"value{i}")
                await asyncio.sleep(0.001)
        
        async def reader():
            for i in range(10):
                await cache.get(f"key{i}")
                await asyncio.sleep(0.001)
        
        await asyncio.gather(writer(), reader())
        
        # Should complete without errors
        assert cache._stats.hits + cache._stats.misses > 0
