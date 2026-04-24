"""
File watcher service for Aider/IronClaw handoff pipeline.

This module monitors the workspace for new task files and triggers
Aider execution when tasks are detected.
"""

from __future__ import annotations

import asyncio
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

import structlog
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .task_schema import Task, TaskStatus, load_task_from_file

logger = structlog.get_logger(__name__)


class TaskFileHandler(FileSystemEventHandler):
    """
    Handles file system events for task files.
    
    Watches for new or modified task files (TASK*.md, TASK*.json)
    and triggers callback functions.
    """
    
    # Pattern for task files
    TASK_PATTERN = re.compile(r'^TASK.*\.(md|json)$', re.IGNORECASE)
    
    def __init__(
        self,
        callback: Callable[[Path], Any],
        workspace_dir: Path,
        debounce_seconds: float = 2.0,
    ):
        self.callback = callback
        self.workspace_dir = Path(workspace_dir)
        self.debounce_seconds = debounce_seconds
        self._pending_tasks: Dict[str, float] = {}
        self._processing: Set[str] = set()
        
        # Start debounce task
        self._loop = asyncio.get_event_loop()
        self._debounce_task = self._loop.create_task(self._debounce_processor())
    
    def is_task_file(self, path: str) -> bool:
        """Check if path matches task file pattern."""
        filename = Path(path).name
        return bool(self.TASK_PATTERN.match(filename))
    
    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events."""
        if not event.is_directory and self.is_task_file(event.src_path):
            self._schedule_task(event.src_path)
    
    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events."""
        if not event.is_directory and self.is_task_file(event.src_path):
            self._schedule_task(event.src_path)
    
    def _schedule_task(self, file_path: str) -> None:
        """Schedule task file for processing with debounce."""
        task_id = Path(file_path).name
        
        # Skip if already processing
        if task_id in self._processing:
            return
        
        # Schedule for processing
        self._pending_tasks[file_path] = datetime.now().timestamp()
        
        logger.info(
            "Task file scheduled for processing",
            file_path=file_path,
            debounce_seconds=self.debounce_seconds,
        )
    
    async def _debounce_processor(self) -> None:
        """Process pending tasks after debounce period."""
        while True:
            await asyncio.sleep(0.5)
            
            now = datetime.now().timestamp()
            to_process = []
            
            for file_path, scheduled_time in list(self._pending_tasks.items()):
                if now - scheduled_time >= self.debounce_seconds:
                    to_process.append(file_path)
                    del self._pending_tasks[file_path]
            
            for file_path in to_process:
                if file_path not in self._processing:
                    self._processing.add(file_path)
                    try:
                        await self._process_task_file(file_path)
                    finally:
                        self._processing.discard(file_path)
    
    async def _process_task_file(self, file_path: str) -> None:
        """Process a task file."""
        path = Path(file_path)
        
        if not path.exists():
            logger.warning("Task file no longer exists", file_path=file_path)
            return
        
        try:
            logger.info("Processing task file", file_path=file_path)
            
            # Load task
            task = load_task_from_file(path)
            
            # Validate task
            if not task.title or not task.description:
                logger.error("Invalid task file: missing required fields", file_path=file_path)
                return
            
            # Call callback
            await self.callback(path, task)
            
        except Exception as e:
            logger.exception(
                "Error processing task file",
                file_path=file_path,
                error=str(e),
            )


class FileWatcher:
    """
    Monitors workspace for task files and triggers Aider execution.
    
    Features:
    - Watches for TASK*.md and TASK*.json files
    - Debounces rapid file changes
    - Integrates with Aider CLI
    """
    
    def __init__(
        self,
        workspace_dir: Path,
        task_callback: Optional[Callable[[Path, Task], Any]] = None,
        debounce_seconds: float = 2.0,
    ):
        self.workspace_dir = Path(workspace_dir)
        self.task_callback = task_callback
        self.debounce_seconds = debounce_seconds
        
        self.observer: Optional[Observer] = None
        self.handler: Optional[TaskFileHandler] = None
        
        logger.info(
            "File watcher initialized",
            workspace_dir=str(self.workspace_dir),
            debounce_seconds=debounce_seconds,
        )
    
    def start(self) -> None:
        """Start watching for task files."""
        if self.observer is not None:
            logger.warning("File watcher already running")
            return
        
        # Create handler
        self.handler = TaskFileHandler(
            callback=self._handle_task,
            workspace_dir=self.workspace_dir,
            debounce_seconds=self.debounce_seconds,
        )
        
        # Start observer
        self.observer = Observer()
        self.observer.schedule(
            self.handler,
            str(self.workspace_dir),
            recursive=False,
        )
        self.observer.start()
        
        logger.info("File watcher started", workspace_dir=str(self.workspace_dir))
    
    def stop(self) -> None:
        """Stop watching for task files."""
        if self.observer is None:
            return
        
        self.observer.stop()
        self.observer.join()
        self.observer = None
        self.handler = None
        
        logger.info("File watcher stopped")
    
    async def _handle_task(self, file_path: Path, task: Task) -> None:
        """Handle discovered task file."""
        if self.task_callback:
            await self.task_callback(file_path, task)
        else:
            logger.info("Task discovered (no callback)", task_id=task.id, title=task.title)
    
    @property
    def is_running(self) -> bool:
        """Check if watcher is running."""
        return self.observer is not None and self.observer.is_alive()


class TaskDiscovery:
    """
    Discovers existing task files in the workspace.
    
    Useful for finding tasks that were created before the watcher started.
    """
    
    def __init__(self, workspace_dir: Path):
        self.workspace_dir = Path(workspace_dir)
    
    def find_tasks(self) -> List[Path]:
        """Find all task files in workspace."""
        patterns = ['TASK*.md', 'TASK*.json', 'task*.md', 'task*.json']
        tasks = []
        
        for pattern in patterns:
            tasks.extend(self.workspace_dir.glob(pattern))
        
        # Sort by modification time (newest first)
        tasks.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        
        logger.info(
            "Discovered task files",
            workspace_dir=str(self.workspace_dir),
            task_count=len(tasks),
        )
        
        return tasks
    
    def find_pending_tasks(self) -> List[Task]:
        """Find all pending tasks in workspace."""
        pending = []
        
        for task_file in self.find_tasks():
            try:
                task = load_task_from_file(task_file)
                if task.status == TaskStatus.PENDING:
                    pending.append(task)
            except Exception as e:
                logger.warning(
                    "Failed to load task file",
                    file_path=str(task_file),
                    error=str(e),
                )
        
        return pending
