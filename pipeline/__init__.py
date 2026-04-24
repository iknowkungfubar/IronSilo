"""
Pipeline module for Aider/IronClaw handoff.

This module provides the infrastructure for agent-to-agent task delegation,
enabling IronClaw to research and create tasks that are then executed by Aider.
"""

from .agent_bridge import AgentBridge, TaskSubmission, TaskUpdate, create_agent_bridge
from .file_watcher import FileWatcher, TaskDiscovery
from .task_schema import (
    AcceptanceCriterion,
    ImplementationNote,
    ResearchFinding,
    Task,
    TaskDependency,
    TaskList,
    TaskPriority,
    TaskStatus,
    load_task_from_file,
    save_task_to_file,
)

__version__ = "1.0.0"

__all__ = [
    # Task schema
    "Task",
    "TaskList",
    "TaskPriority",
    "TaskStatus",
    "TaskDependency",
    "AcceptanceCriterion",
    "ResearchFinding",
    "ImplementationNote",
    "load_task_from_file",
    "save_task_to_file",
    
    # File watcher
    "FileWatcher",
    "TaskDiscovery",
    
    # Agent bridge
    "AgentBridge",
    "TaskSubmission",
    "TaskUpdate",
    "create_agent_bridge",
]
