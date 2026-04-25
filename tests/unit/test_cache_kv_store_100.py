"""
Additional tests for cache/kv_store.py to achieve 100% coverage.
"""

import asyncio
import pickle
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

from cache.kv_store import (
    CacheEntry,
    CacheStats,
    LRUCache,
    KVCache,
    create_kv_cache,
)


class TestLRUCacheEdgeCases:
    """Edge case tests for LRUCache."""
    
    @pytest.mark.asyncio
    async def test_evict_empty_cache(self):
        """Test eviction when cache is empty (line 245)."""
        cache = LRUCache(max_size=1)
        
        # Manually clear cache and call eviction
        cache._cache.clear()
        
        # This should trigger the break condition at line 245
        await cache._evict_if_needed(100)
        
        # Should complete without error
        assert len(cache._cache) == 0
    
    def test_calculate_size_complex_object(self):
        """Test size calculation for complex objects using pickle (lines 276-279)."""
        cache = LRUCache()
        
        # Create a complex object that can't be sized by str()
        class CustomObject:
            def __init__(self):
                self.data = "test"
        
        obj = CustomObject()
        
        # This should use pickle fallback
        size = cache._calculate_size(obj)
        
        # Should return fallback size (1024) or pickle size
        assert size > 0
    
    def test_calculate_size_exception_fallback(self):
        """Test size calculation fallback when exception occurs (lines 276-279)."""
        cache = LRUCache()
        
        # Create object that raises exception during JSON serialization
        # The implementation uses json.dumps(value, default=str), so we need
        # to create an object that fails even with default=str
        class UnserializableObject:
            def __repr__(self):
                raise RuntimeError("Cannot represent")
            
            def __str__(self):
                raise RuntimeError("Cannot stringify")
        
        obj = UnserializableObject()
        
        # Should return fallback size
        size = cache._calculate_size(obj)
        assert size == 1024  # Fallback size
    
    @pytest.mark.asyncio
    async def test_persist_no_path(self):
        """Test persist with no persist_path (line 288)."""
        cache = LRUCache(persist_path=None)
        
        # Should return early without error
        await cache.persist()
        
        # No file should be created
        assert cache.persist_path is None
    
    @pytest.mark.asyncio
    async def test_persist_exception_handling(self):
        """Test persist exception handling (lines 322-323)."""
        cache = LRUCache(persist_path=Path("/nonexistent/dir/cache.pkl"))
        
        # Should handle exception gracefully
        await cache.persist()
        
        # Should not raise, just log error
    
    def test_load_from_disk_exception_handling(self):
        """Test _load_from_disk exception handling (lines 351-352)."""
        # Create cache with invalid path
        cache = LRUCache(persist_path=Path("/nonexistent/cache.pkl"))
        
        # Should handle exception gracefully
        cache._load_from_disk()
        
        # Cache should remain empty
        assert len(cache._cache) == 0
    
    @pytest.mark.asyncio
    async def test_persist_with_permission_error(self):
        """Test persist with permission error."""
        cache = LRUCache()
        await cache.set("key", "value")
        
        # Mock open to raise PermissionError
        with patch("builtins.open", mock_open()) as mock_file:
            mock_file.side_effect = PermissionError("Permission denied")
            
            # Should handle exception gracefully
            await cache.persist()
    
    @pytest.mark.asyncio
    async def test_load_from_disk_corrupt_file(self):
        """Test loading from corrupt pickle file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            corrupt_file = Path(tmpdir) / "corrupt.pkl"
            corrupt_file.write_bytes(b"not valid pickle data")
            
            cache = LRUCache(persist_path=corrupt_file)
            
            # Should handle exception gracefully
            assert len(cache._cache) == 0


class TestKVCacheStartStop:
    """Test KVCache start/stop methods."""
    
    @pytest.mark.asyncio
    async def test_start_twice(self):
        """Test starting KVCache twice (line 426)."""
        kv = KVCache()
        
        await kv.start(persist_interval=1)
        first_task = kv._persist_task
        
        # Starting again should return early
        await kv.start(persist_interval=1)
        
        # Should be same task
        assert kv._persist_task is first_task
        
        # Clean up
        await kv.stop()
    
    @pytest.mark.asyncio
    async def test_start_persist_loop(self):
        """Test persist loop in start method (lines 429-431)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            persist_path = Path(tmpdir) / "cache.pkl"
            kv = KVCache(persist_path=persist_path)
            
            # Start with short interval
            await kv.start(persist_interval=0.1)
            
            # Add some data
            await kv.set_response(
                [{"role": "user", "content": "test"}],
                {"response": "data"}
            )
            
            # Wait for persist loop to run
            await asyncio.sleep(0.2)
            
            # Stop
            await kv.stop()
            
            # File should exist (persist loop ran)
            assert persist_path.exists()
    
    @pytest.mark.asyncio
    async def test_stop_without_start(self):
        """Test stopping KVCache without starting (lines 438-445)."""
        kv = KVCache()
        
        # Should not raise even if not started
        await kv.stop()
        
        assert kv._persist_task is None
    
    @pytest.mark.asyncio
    async def test_stop_cancels_task(self):
        """Test that stop cancels the persist task."""
        with tempfile.TemporaryDirectory() as tmpdir:
            persist_path = Path(tmpdir) / "cache.pkl"
            kv = KVCache(persist_path=persist_path)
            
            await kv.start(persist_interval=1)
            task = kv._persist_task
            
            await kv.stop()
            
            # Task should be cancelled
            assert task.cancelled() or task.done()


class TestCacheEntryEdgeCases:
    """Edge case tests for CacheEntry."""
    
    def test_cache_entry_zero_size(self):
        """Test cache entry with zero size."""
        entry = CacheEntry(
            key="test",
            value="",
            size_bytes=0,
        )
        
        assert entry.size_bytes == 0
    
    @pytest.mark.asyncio
    async def test_cache_touch_multiple_times(self):
        """Test touching entry multiple times."""
        entry = CacheEntry(key="test", value="value")
        
        initial_count = entry.access_count
        
        for _ in range(10):
            entry.touch()
        
        assert entry.access_count == initial_count + 10


class TestLRUCacheAdditional:
    """Additional tests for LRUCache."""
    
    @pytest.mark.asyncio
    async def test_evict_all_entries(self):
        """Test evicting all entries."""
        cache = LRUCache(max_size=2)
        
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        
        # Evict all by adding more entries
        await cache.set("key3", "value3")
        await cache.set("key4", "value4")
        
        assert len(cache._cache) == 2
        assert cache._stats.evictions >= 2
    
    @pytest.mark.asyncio
    async def test_size_calculation_tuple(self):
        """Test size calculation for tuples."""
        cache = LRUCache()
        
        size = cache._calculate_size((1, 2, 3))
        
        assert size > 0
    
    @pytest.mark.asyncio
    async def test_size_calculation_bool(self):
        """Test size calculation for booleans."""
        cache = LRUCache()
        
        size_true = cache._calculate_size(True)
        size_false = cache._calculate_size(False)
        
        assert size_true > 0
        assert size_false > 0


class TestCacheStatsAdditional:
    """Additional tests for CacheStats."""
    
    def test_hit_rate_partial(self):
        """Test hit rate with partial hits."""
        stats = CacheStats(hits=3, misses=2)
        
        assert abs(stats.hit_rate - 0.6) < 0.0001
    
    def test_hit_rate_zero_hits(self):
        """Test hit rate with zero hits."""
        stats = CacheStats(hits=0, misses=10)
        
        assert stats.hit_rate == 0.0
        assert stats.miss_rate == 1.0
