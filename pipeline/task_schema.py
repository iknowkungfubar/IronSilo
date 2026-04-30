"""
Task schema for Aider/IronClaw handoff pipeline.

This module defines the standardized task format for agent-to-agent
communication, enabling IronClaw to delegate implementation tasks to Aider.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator
import structlog

logger = structlog.get_logger(__name__)


class TaskPriority(str, Enum):
    """Task priority levels."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(str, Enum):
    """Task status values."""
    
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AcceptanceCriterion(BaseModel):
    """Individual acceptance criterion for a task."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str
    verified: bool = False
    verification_notes: Optional[str] = None
    
    @field_validator('description')
    @classmethod
    def description_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Description must not be empty')
        return v.strip()


class TaskDependency(BaseModel):
    """Dependency on another task."""
    
    task_id: str
    relationship: str = "blocks"  # blocks, related_to, requires
    notes: Optional[str] = None


class ResearchFinding(BaseModel):
    """Research finding from IronClaw."""
    
    source: str
    content: str
    url: Optional[str] = None
    relevance_score: float = Field(default=1.0, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CodeReference(BaseModel):
    """Reference to existing code."""
    
    file_path: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    content: Optional[str] = None
    language: Optional[str] = None


class ImplementationNote(BaseModel):
    """Notes for implementation."""
    
    content: str
    author: str = "ironclaw"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    priority: TaskPriority = TaskPriority.MEDIUM


class Task(BaseModel):
    """
    Task model for agent handoff.
    
    This is the standardized format for tasks passed between IronClaw
    and Aider during the handoff pipeline.
    """
    
    # Identification
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    
    # Status and priority
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    
    # Research and context
    research_findings: List[ResearchFinding] = Field(default_factory=list)
    requirements: List[str] = Field(default_factory=list)
    acceptance_criteria: List[AcceptanceCriterion] = Field(default_factory=list)
    code_references: List[CodeReference] = Field(default_factory=list)
    implementation_notes: List[ImplementationNote] = Field(default_factory=list)
    
    # Dependencies and relationships
    depends_on: List[TaskDependency] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    
    # Assignment and timing
    assigned_to: Optional[str] = None
    estimated_effort: Optional[str] = None  # e.g., "2 hours", "1 day"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Results (populated after completion)
    implementation_files: List[str] = Field(default_factory=list)
    test_files: List[str] = Field(default_factory=list)
    result_notes: Optional[str] = None
    error_message: Optional[str] = None
    
    @field_validator('title')
    @classmethod
    def title_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Title must not be empty')
        return v.strip()
    
    @field_validator('description')
    @classmethod
    def description_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Description must not be empty')
        return v.strip()
    
    @model_validator(mode='after')
    def update_timestamps(self) -> 'Task':
        """Update timestamps based on status changes."""
        now = datetime.now(timezone.utc)
        
        if self.status == TaskStatus.IN_PROGRESS and self.started_at is None:
            self.started_at = now
        
        if self.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            if self.completed_at is None:
                self.completed_at = now
        
        self.updated_at = now
        return self
    
    def start(self, assigned_to: Optional[str] = None) -> None:
        """Mark task as in progress."""
        self.status = TaskStatus.IN_PROGRESS
        if assigned_to:
            self.assigned_to = assigned_to
        self.started_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def complete(
        self,
        implementation_files: Optional[List[str]] = None,
        test_files: Optional[List[str]] = None,
        notes: Optional[str] = None,
    ) -> None:
        """Mark task as completed."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        if implementation_files:
            self.implementation_files = implementation_files
        if test_files:
            self.test_files = test_files
        if notes:
            self.result_notes = notes
        self.updated_at = datetime.now(timezone.utc)
    
    def fail(self, error_message: str) -> None:
        """Mark task as failed."""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.now(timezone.utc)
        self.error_message = error_message
        self.updated_at = datetime.now(timezone.utc)
    
    def cancel(self) -> None:
        """Mark task as cancelled."""
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def add_research_finding(self, finding: ResearchFinding) -> None:
        """Add a research finding to the task."""
        self.research_findings.append(finding)
        self.updated_at = datetime.now(timezone.utc)
    
    def add_implementation_note(self, content: str, priority: TaskPriority = TaskPriority.MEDIUM) -> None:
        """Add an implementation note."""
        self.implementation_notes.append(
            ImplementationNote(content=content, priority=priority)
        )
        self.updated_at = datetime.now(timezone.utc)
    
    def add_acceptance_criterion(self, description: str) -> str:
        """Add an acceptance criterion and return its ID."""
        criterion = AcceptanceCriterion(description=description)
        self.acceptance_criteria.append(criterion)
        self.updated_at = datetime.now(timezone.utc)
        return criterion.id
    
    def verify_criterion(self, criterion_id: str, notes: Optional[str] = None) -> bool:
        """Mark an acceptance criterion as verified."""
        for criterion in self.acceptance_criteria:
            if criterion.id == criterion_id:
                criterion.verified = True
                if notes:
                    criterion.verification_notes = notes
                self.updated_at = datetime.now(timezone.utc)
                return True
        return False
    
    @property
    def is_complete(self) -> bool:
        """Check if task is completed successfully."""
        return self.status == TaskStatus.COMPLETED
    
    @property
    def is_failed(self) -> bool:
        """Check if task has failed."""
        return self.status == TaskStatus.FAILED
    
    @property
    def all_criteria_met(self) -> bool:
        """Check if all acceptance criteria are verified."""
        if not self.acceptance_criteria:
            return True
        return all(c.verified for c in self.acceptance_criteria)
    
    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage based on acceptance criteria."""
        if not self.acceptance_criteria:
            if self.status == TaskStatus.COMPLETED:
                return 100.0
            return 0.0
        
        verified_count = sum(1 for c in self.acceptance_criteria if c.verified)
        return (verified_count / len(self.acceptance_criteria)) * 100.0


class TaskList(BaseModel):
    """Collection of tasks with metadata."""
    
    tasks: List[Task] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def add_task(self, task: Task) -> str:
        """Add a task and return its ID."""
        self.tasks.append(task)
        self.updated_at = datetime.now(timezone.utc)
        return task.id
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """Get all tasks with a specific status."""
        return [t for t in self.tasks if t.status == status]
    
    def get_tasks_by_priority(self, priority: TaskPriority) -> List[Task]:
        """Get all tasks with a specific priority."""
        return [t for t in self.tasks if t.priority == priority]
    
    @property
    def pending_count(self) -> int:
        return len(self.get_tasks_by_status(TaskStatus.PENDING))
    
    @property
    def in_progress_count(self) -> int:
        return len(self.get_tasks_by_status(TaskStatus.IN_PROGRESS))
    
    @property
    def completed_count(self) -> int:
        return len(self.get_tasks_by_status(TaskStatus.COMPLETED))
    
    @property
    def failed_count(self) -> int:
        return len(self.get_tasks_by_status(TaskStatus.FAILED))


def load_task_from_file(file_path: Union[str, Path]) -> Task:
    """
    Load a task from a JSON or Markdown file.
    
    Supports:
    - JSON files (.json)
    - Markdown files with YAML frontmatter (.md)
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Task file not found: {path}")
    
    if path.suffix == '.json':
        return Task.model_validate_json(path.read_text())
    
    elif path.suffix in ['.md', '.markdown']:
        # Try to parse YAML frontmatter
        content = path.read_text()
        
        # Check for frontmatter
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                frontmatter = parts[1]
                body = parts[2]
                
                # Parse YAML frontmatter
                import yaml
                data = yaml.safe_load(frontmatter)
                
                # Add body as description if not present
                if 'description' not in data and body.strip():
                    data['description'] = body.strip()
                
                return Task(**data)
        
        # No frontmatter, treat entire content as description
        return Task(
            title=path.stem.replace('_', ' ').title(),
            description=content,
        )
    
    else:
        raise ValueError(f"Unsupported file format: {path.suffix}")


def save_task_to_file(task: Task, file_path: Union[str, Path], format: str = 'json') -> Path:
    """
    Save a task to a file.
    
    Args:
        task: Task to save
        file_path: Output file path
        format: Output format ('json' or 'markdown')
    
    Returns:
        Path to saved file
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    if format == 'json':
        path.write_text(task.model_dump_json(indent=2))
    
    elif format == 'markdown':
        # Create markdown with YAML frontmatter
        frontmatter = task.model_dump_json(indent=2)
        markdown = f"""---
{frontmatter}
---

{task.description}

## Requirements

{chr(10).join(f'- {req}' for req in task.requirements)}

## Acceptance Criteria

{chr(10).join(f'- [ ] {c.description}' for c in task.acceptance_criteria)}

## Research Findings

{chr(10).join(f'### {f.source}' + chr(10) + f.content for f in task.research_findings)}
"""
        path.write_text(markdown)
    
    else:
        raise ValueError(f"Unsupported format: {format}")
    
    return path
