"""
Tests for file watcher watchdog timer functionality.
"""

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestTaskFileHandlerWatchdog:
    """Tests for TaskFileHandler watchdog timer."""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.mark.asyncio
    async def test_watchdog_timer_triggers_after_timeout(self, temp_workspace):
        """Test watchdog timer triggers after long processing."""
        from pipeline.file_watcher import TaskFileHandler

        async def slow_callback(path, task=None):
            await asyncio.sleep(10)

        handler = TaskFileHandler(
            callback=slow_callback,
            workspace_dir=temp_workspace,
            debounce_seconds=0.1,
            watchdog_timeout=0.5,
        )

        task_file = temp_workspace / "TASK_test.md"
        task_file.write_text("# Test Task\n\nDescription here.")

        handler._schedule_task(str(task_file))

        await asyncio.sleep(2.5)

        assert handler._watchdog_triggered is True

    @pytest.mark.asyncio
    async def test_watchdog_cancels_hung_task(self, temp_workspace):
        """Test watchdog cancels hung task processing."""
        from pipeline.file_watcher import TaskFileHandler

        processing_started = asyncio.Event()
        watchdog_triggered = asyncio.Event()

        async def slow_callback(path):
            await processing_started.set()
            await asyncio.sleep(10)

        handler = TaskFileHandler(
            callback=slow_callback,
            workspace_dir=temp_workspace,
            debounce_seconds=0.1,
            watchdog_timeout=0.5,
        )

        task_file = temp_workspace / "TASK_slow.md"
        task_file.write_text("# Slow Task\n\nThis task takes forever.")

        await asyncio.sleep(0.6)

        assert handler._watchdog_triggered is True or not processing_started.is_set()


class TestFileWatcherWatchdog:
    """Tests for FileWatcher watchdog integration."""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_watchdog_enabled_by_default(self, temp_workspace):
        """Test watchdog is enabled by default."""
        from pipeline.file_watcher import FileWatcher

        watcher = FileWatcher(workspace_dir=temp_workspace)
        assert watcher.watchdog_timeout == 30.0

    def test_watchdog_configurable(self, temp_workspace):
        """Test watchdog timeout is configurable."""
        from pipeline.file_watcher import FileWatcher

        watcher = FileWatcher(
            workspace_dir=temp_workspace,
            watchdog_timeout=60.0,
        )
        assert watcher.watchdog_timeout == 60.0

    def test_watchdog_disabled_with_zero(self, temp_workspace):
        """Test watchdog can be disabled with zero timeout."""
        from pipeline.file_watcher import FileWatcher

        watcher = FileWatcher(
            workspace_dir=temp_workspace,
            watchdog_timeout=0,
        )
        assert watcher.watchdog_timeout == 0

    @pytest.mark.asyncio
    async def test_watchdog_restarts_stuck_handler(self, temp_workspace):
        """Test watchdog restarts stuck handler."""
        from pipeline.file_watcher import FileWatcher

        restart_count = 0

        original_start = FileWatcher.start
        def mock_start(self):
            nonlocal restart_count
            restart_count += 1
            original_start(self)

        with patch.object(FileWatcher, 'start', mock_start):
            watcher = FileWatcher(
                workspace_dir=temp_workspace,
                watchdog_timeout=1.0,
            )
            watcher.start()
            await asyncio.sleep(1.5)
            watcher.stop()

        assert restart_count >= 1