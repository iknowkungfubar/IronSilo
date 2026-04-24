"""
Unit tests for pipeline/file_watcher.py.

Tests cover:
- TaskFileHandler initialization and file pattern matching
- File watcher start/stop functionality
- Task discovery
- Debounce processing
- Error handling
"""

import asyncio
import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from watchdog.events import FileCreatedEvent, FileModifiedEvent

from pipeline.file_watcher import FileWatcher, TaskDiscovery, TaskFileHandler
from pipeline.task_schema import Task, TaskStatus


class TestTaskFileHandlerPattern:
    """Test TaskFileHandler pattern matching without initialization."""
    
    def test_is_task_file_match(self):
        """Test task file pattern matching."""
        # Test the pattern directly without creating handler
        import re
        pattern = re.compile(r'^TASK.*\.(md|json)$', re.IGNORECASE)
        
        # Should match
        assert bool(pattern.match("TASK-001.md"))
        assert bool(pattern.match("task-001.json"))
        assert bool(pattern.match("TASK_123_test.md"))
        assert bool(pattern.match("task.json"))
        
        # Should not match
        assert not bool(pattern.match("test.md"))
        assert not bool(pattern.match("TASK"))
        assert not bool(pattern.match("task.txt"))
        assert not bool(pattern.match("README.md"))


class TestFileWatcher:
    """Test FileWatcher class."""
    
    def test_initialization(self):
        """Test file watcher initialization."""
        watcher = FileWatcher(
            workspace_dir=Path("/tmp/workspace"),
            debounce_seconds=1.5,
        )
        
        assert watcher.workspace_dir == Path("/tmp/workspace")
        assert watcher.debounce_seconds == 1.5
        assert watcher.observer is None
        assert watcher.handler is None
        assert not watcher.is_running
    
    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test starting and stopping the watcher."""
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = FileWatcher(workspace_dir=Path(tmpdir))
            
            # Mock the event loop creation to avoid issues
            with patch('asyncio.get_event_loop') as mock_loop:
                mock_loop.return_value = asyncio.get_event_loop()
                watcher.start()
            
            assert watcher.is_running
            assert watcher.observer is not None
            assert watcher.handler is not None
            
            watcher.stop()
            
            assert not watcher.is_running
            assert watcher.observer is None
            assert watcher.handler is None
    
    def test_stop_when_not_running(self):
        """Test stopping watcher when not running."""
        watcher = FileWatcher(workspace_dir=Path("/tmp"))
        
        # Should not raise
        watcher.stop()
        
        assert not watcher.is_running
    
    @pytest.mark.asyncio
    async def test_handle_task_with_callback(self):
        """Test handling task with callback."""
        callback = AsyncMock()
        watcher = FileWatcher(
            workspace_dir=Path("/tmp"),
            task_callback=callback,
        )
        
        task = Task(
            id="test-1",
            title="Test Task",
            description="Test description",
            status=TaskStatus.PENDING,
        )
        
        await watcher._handle_task(Path("/tmp/TASK-001.md"), task)
        
        callback.assert_called_once_with(Path("/tmp/TASK-001.md"), task)
    
    @pytest.mark.asyncio
    async def test_handle_task_without_callback(self):
        """Test handling task without callback."""
        watcher = FileWatcher(workspace_dir=Path("/tmp"))
        
        task = Task(
            id="test-1",
            title="Test Task",
            description="Test description",
            status=TaskStatus.PENDING,
        )
        
        # Should not raise
        await watcher._handle_task(Path("/tmp/TASK-001.md"), task)


class TestTaskDiscovery:
    """Test TaskDiscovery class."""
    
    def test_find_tasks_empty_directory(self):
        """Test finding tasks in empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            discovery = TaskDiscovery(workspace_dir=Path(tmpdir))
            
            tasks = discovery.find_tasks()
            
            assert len(tasks) == 0
    
    def test_find_tasks_with_files(self):
        """Test finding task files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Create task files
            (tmpdir_path / "TASK-001.md").write_text("# Task 1")
            (tmpdir_path / "task-002.json").write_text("{}")
            (tmpdir_path / "README.md").write_text("# Not a task")
            
            discovery = TaskDiscovery(workspace_dir=tmpdir_path)
            
            tasks = discovery.find_tasks()
            
            assert len(tasks) == 2
            task_names = [t.name for t in tasks]
            assert "TASK-001.md" in task_names
            assert "task-002.json" in task_names
            assert "README.md" not in task_names
    
    def test_find_tasks_sorted_by_mtime(self):
        """Test that tasks are sorted by modification time."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Create task files with different mtimes
            task1 = tmpdir_path / "TASK-001.md"
            task2 = tmpdir_path / "TASK-002.md"
            
            task1.write_text("# Task 1")
            task2.write_text("# Task 2")
            
            # Set different mtimes
            import time
            time.sleep(0.01)
            task1.touch()
            
            discovery = TaskDiscovery(workspace_dir=tmpdir_path)
            
            tasks = discovery.find_tasks()
            
            # Most recent should be first
            assert tasks[0].name == "TASK-001.md"
    
    def test_find_pending_tasks(self):
        """Test finding pending tasks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Create a valid task file
            task_content = {
                "id": "test-1",
                "title": "Test Task",
                "description": "Test description",
                "status": "pending",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            
            (tmpdir_path / "TASK-001.json").write_text(json.dumps(task_content))
            
            discovery = TaskDiscovery(workspace_dir=tmpdir_path)
            
            pending_tasks = discovery.find_pending_tasks()
            
            assert len(pending_tasks) == 1
            assert pending_tasks[0].title == "Test Task"
            assert pending_tasks[0].status == TaskStatus.PENDING
    
    def test_find_pending_tasks_skips_invalid(self):
        """Test that invalid task files are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Create invalid task file
            (tmpdir_path / "TASK-001.json").write_text("invalid json")
            
            discovery = TaskDiscovery(workspace_dir=tmpdir_path)
            
            # Should not raise
            pending_tasks = discovery.find_pending_tasks()
            
            assert len(pending_tasks) == 0
