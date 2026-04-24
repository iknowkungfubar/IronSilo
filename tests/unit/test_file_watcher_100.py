"""
Comprehensive unit tests for pipeline/file_watcher.py to achieve 100% coverage.

Tests cover:
- TaskFileHandler initialization and debounce processor
- File event handling (on_created, on_modified)
- Task scheduling with debounce
- Task file processing with error handling
- Task discovery edge cases
"""

import asyncio
import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

# We need to mock watchdog before importing file_watcher
# Create mock modules
mock_watchdog = MagicMock()
mock_watchdog_events = MagicMock()
mock_watchdog_observer = MagicMock()


class MockFileSystemEvent:
    """Mock FileSystemEvent for testing."""
    def __init__(self, src_path: str, is_directory: bool = False):
        self.src_path = src_path
        self.is_directory = is_directory


class MockObserver:
    """Mock Observer for testing."""
    def __init__(self):
        self._running = False
        self._handler = None
        self._path = None
        self._recursive = False
    
    def schedule(self, handler, path, recursive=False):
        self._handler = handler
        self._path = path
        self._recursive = recursive
    
    def start(self):
        self._running = True
    
    def stop(self):
        self._running = False
    
    def join(self):
        pass
    
    def is_alive(self):
        return self._running


# Patch the imports before importing file_watcher
@pytest.fixture(autouse=True)
def mock_watchdog_imports():
    """Mock watchdog imports for all tests."""
    with patch.dict('sys.modules', {
        'watchdog': mock_watchdog,
        'watchdog.events': mock_watchdog_events,
        'watchdog.observers': mock_watchdog_observer,
    }):
        # Set up mock classes
        mock_watchdog_events.FileSystemEventHandler = object
        mock_watchdog_events.FileSystemEvent = MockFileSystemEvent
        mock_watchdog_observer.Observer = MockObserver
        
        # Now we can import file_watcher
        import pipeline.file_watcher as fw
        # Reload to pick up mocks
        import importlib
        importlib.reload(fw)
        yield fw


class TestTaskFileHandler:
    """Test TaskFileHandler class."""
    
    @pytest.mark.asyncio
    async def test_handler_initialization(self, mock_watchdog_imports):
        """Test TaskFileHandler initialization."""
        fw = mock_watchdog_imports
        callback = AsyncMock()
        
        handler = fw.TaskFileHandler(
            callback=callback,
            workspace_dir=Path("/tmp/workspace"),
            debounce_seconds=1.5,
        )
        
        assert handler.callback == callback
        assert handler.workspace_dir == Path("/tmp/workspace")
        assert handler.debounce_seconds == 1.5
        assert handler._pending_tasks == {}
        assert handler._processing == set()
        assert handler._debounce_task is not None
        
        # Clean up the task
        handler._debounce_task.cancel()
        try:
            await handler._debounce_task
        except asyncio.CancelledError:
            pass
    
    @pytest.mark.asyncio
    async def test_is_task_file(self, mock_watchdog_imports):
        """Test is_task_file method."""
        fw = mock_watchdog_imports
        
        handler = fw.TaskFileHandler(
            callback=AsyncMock(),
            workspace_dir=Path("/tmp"),
        )
        
        # Should match
        assert handler.is_task_file("TASK-001.md")
        assert handler.is_task_file("task-001.json")
        assert handler.is_task_file("TASK_123_test.md")
        assert handler.is_task_file("/path/to/task.json")
        
        # Should not match
        assert not handler.is_task_file("test.md")
        assert not handler.is_task_file("TASK")
        assert not handler.is_task_file("task.txt")
        assert not handler.is_task_file("README.md")
    
    @pytest.mark.asyncio
    async def test_on_created_non_task_file(self, mock_watchdog_imports):
        """Test on_created with non-task file."""
        fw = mock_watchdog_imports
        
        handler = fw.TaskFileHandler(
            callback=AsyncMock(),
            workspace_dir=Path("/tmp"),
        )
        
        event = MockFileSystemEvent("/tmp/test.txt", is_directory=False)
        handler.on_created(event)
        
        # Should not schedule
        assert len(handler._pending_tasks) == 0
        
        # Clean up
        handler._debounce_task.cancel()
        try:
            await handler._debounce_task
        except asyncio.CancelledError:
            pass
    
    @pytest.mark.asyncio
    async def test_on_created_directory(self, mock_watchdog_imports):
        """Test on_created with directory."""
        fw = mock_watchdog_imports
        
        handler = fw.TaskFileHandler(
            callback=AsyncMock(),
            workspace_dir=Path("/tmp"),
        )
        
        event = MockFileSystemEvent("/tmp/TASK-001.md", is_directory=True)
        handler.on_created(event)
        
        # Should not schedule directories
        assert len(handler._pending_tasks) == 0
        
        # Clean up
        handler._debounce_task.cancel()
        try:
            await handler._debounce_task
        except asyncio.CancelledError:
            pass
    
    @pytest.mark.asyncio
    async def test_on_created_task_file(self, mock_watchdog_imports):
        """Test on_created with task file."""
        fw = mock_watchdog_imports
        
        handler = fw.TaskFileHandler(
            callback=AsyncMock(),
            workspace_dir=Path("/tmp"),
            debounce_seconds=1.0,
        )
        
        event = MockFileSystemEvent("/tmp/TASK-001.md", is_directory=False)
        handler.on_created(event)
        
        # Should schedule
        assert "/tmp/TASK-001.md" in handler._pending_tasks
        
        # Clean up
        handler._debounce_task.cancel()
        try:
            await handler._debounce_task
        except asyncio.CancelledError:
            pass
    
    @pytest.mark.asyncio
    async def test_on_modified(self, mock_watchdog_imports):
        """Test on_modified handler."""
        fw = mock_watchdog_imports
        
        handler = fw.TaskFileHandler(
            callback=AsyncMock(),
            workspace_dir=Path("/tmp"),
        )
        
        event = MockFileSystemEvent("/tmp/TASK-002.json", is_directory=False)
        handler.on_modified(event)
        
        assert "/tmp/TASK-002.json" in handler._pending_tasks
        
        # Clean up
        handler._debounce_task.cancel()
        try:
            await handler._debounce_task
        except asyncio.CancelledError:
            pass
    
    @pytest.mark.asyncio
    async def test_schedule_task_already_processing(self, mock_watchdog_imports):
        """Test scheduling task that is already processing."""
        fw = mock_watchdog_imports
        
        handler = fw.TaskFileHandler(
            callback=AsyncMock(),
            workspace_dir=Path("/tmp"),
        )
        
        # Add to processing set
        handler._processing.add("TASK-001.md")
        
        # Try to schedule
        handler._schedule_task("/tmp/TASK-001.md")
        
        # Should not add to pending
        assert "/tmp/TASK-001.md" not in handler._pending_tasks
        
        # Clean up
        handler._debounce_task.cancel()
        try:
            await handler._debounce_task
        except asyncio.CancelledError:
            pass
    
    @pytest.mark.asyncio
    async def test_process_task_file_success(self, mock_watchdog_imports):
        """Test successfully processing a task file."""
        fw = mock_watchdog_imports
        
        # Create a temp file to be processed
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', prefix='TASK-001', delete=False) as f:
            f.write("# Test Task\n\nDescription here.")
            temp_path = f.name
        
        try:
            callback = AsyncMock()
            handler = fw.TaskFileHandler(
                callback=callback,
                workspace_dir=Path(temp_path).parent,
                debounce_seconds=1.0,
            )
            
            # Mock load_task_from_file
            mock_task = MagicMock()
            mock_task.title = "Test Task"
            mock_task.description = "Test description"
            
            with patch.object(fw, 'load_task_from_file', return_value=mock_task):
                await handler._process_task_file(temp_path)
            
            # Callback should have been called
            callback.assert_called_once()
            # Check the callback was called with the right arguments
            call_args = callback.call_args
            assert call_args[0][0] == Path(temp_path)
            assert call_args[0][1] == mock_task
        finally:
            Path(temp_path).unlink()
        
        # Clean up
        handler._debounce_task.cancel()
        try:
            await handler._debounce_task
        except asyncio.CancelledError:
            pass
    
    @pytest.mark.asyncio
    async def test_process_task_file_not_exists(self, mock_watchdog_imports):
        """Test processing task file that doesn't exist."""
        fw = mock_watchdog_imports
        
        handler = fw.TaskFileHandler(
            callback=AsyncMock(),
            workspace_dir=Path("/tmp"),
        )
        
        # Process non-existent file
        await handler._process_task_file("/tmp/NONEXISTENT.md")
        
        # Callback should not be called
        assert not handler.callback.called
        
        # Clean up
        handler._debounce_task.cancel()
        try:
            await handler._debounce_task
        except asyncio.CancelledError:
            pass
    
    @pytest.mark.asyncio
    async def test_process_task_file_invalid_task(self, mock_watchdog_imports):
        """Test processing task file with missing required fields."""
        fw = mock_watchdog_imports
        
        handler = fw.TaskFileHandler(
            callback=AsyncMock(),
            workspace_dir=Path("/tmp"),
        )
        
        # Create a task with missing fields
        mock_task = MagicMock()
        mock_task.title = ""  # Missing title
        mock_task.description = "Description"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# Task")
            temp_path = f.name
        
        try:
            with patch.object(fw, 'load_task_from_file', return_value=mock_task):
                await handler._process_task_file(temp_path)
            
            # Callback should not be called for invalid task
            assert not handler.callback.called
        finally:
            Path(temp_path).unlink()
        
        # Clean up
        handler._debounce_task.cancel()
        try:
            await handler._debounce_task
        except asyncio.CancelledError:
            pass
    
    @pytest.mark.asyncio
    async def test_process_task_file_error_handling(self, mock_watchdog_imports):
        """Test processing task file with exception."""
        fw = mock_watchdog_imports
        
        handler = fw.TaskFileHandler(
            callback=AsyncMock(),
            workspace_dir=Path("/tmp"),
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# Task")
            temp_path = f.name
        
        try:
            with patch.object(fw, 'load_task_from_file', side_effect=Exception("Parse error")):
                # Should not raise
                await handler._process_task_file(temp_path)
        finally:
            Path(temp_path).unlink()
        
        # Clean up
        handler._debounce_task.cancel()
        try:
            await handler._debounce_task
        except asyncio.CancelledError:
            pass


class TestFileWatcher:
    """Test FileWatcher class."""
    
    def test_start_already_running(self, mock_watchdog_imports):
        """Test starting watcher when already running."""
        fw = mock_watchdog_imports
        
        watcher = fw.FileWatcher(workspace_dir=Path("/tmp"))
        
        # Mock observer as running
        watcher.observer = MockObserver()
        watcher.observer.start()
        
        # Try to start again
        watcher.start()
        
        # Should not create new handler
        assert watcher.handler is None
    
    def test_is_running_observer_alive(self, mock_watchdog_imports):
        """Test is_running when observer is alive."""
        fw = mock_watchdog_imports
        
        watcher = fw.FileWatcher(workspace_dir=Path("/tmp"))
        
        observer = MockObserver()
        observer.start()
        watcher.observer = observer
        
        assert watcher.is_running
    
    def test_is_running_observer_not_alive(self, mock_watchdog_imports):
        """Test is_running when observer is not alive."""
        fw = mock_watchdog_imports
        
        watcher = fw.FileWatcher(workspace_dir=Path("/tmp"))
        
        observer = MockObserver()
        watcher.observer = observer
        
        assert not watcher.is_running


class TestTaskDiscovery:
    """Test TaskDiscovery class."""
    
    def test_find_tasks_empty(self, mock_watchdog_imports):
        """Test finding tasks in empty directory."""
        fw = mock_watchdog_imports
        
        with tempfile.TemporaryDirectory() as tmpdir:
            discovery = fw.TaskDiscovery(workspace_dir=Path(tmpdir))
            tasks = discovery.find_tasks()
            assert len(tasks) == 0
    
    def test_find_pending_tasks_invalid_json(self, mock_watchdog_imports):
        """Test finding pending tasks with invalid JSON."""
        fw = mock_watchdog_imports
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Create invalid JSON task file
            (tmpdir_path / "TASK-001.json").write_text("not valid json")
            
            discovery = fw.TaskDiscovery(workspace_dir=tmpdir_path)
            pending = discovery.find_pending_tasks()
            
            # Should skip invalid file
            assert len(pending) == 0
    
    def test_find_pending_tasks_non_pending_status(self, mock_watchdog_imports):
        """Test finding pending tasks skips non-pending tasks."""
        fw = mock_watchdog_imports
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Create a completed task file
            task_content = {
                "id": "test-1",
                "title": "Test Task",
                "description": "Test description",
                "status": "completed",  # Not pending
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            
            (tmpdir_path / "TASK-001.json").write_text(json.dumps(task_content))
            
            discovery = fw.TaskDiscovery(workspace_dir=tmpdir_path)
            pending = discovery.find_pending_tasks()
            
            # Should not include completed task
            assert len(pending) == 0
