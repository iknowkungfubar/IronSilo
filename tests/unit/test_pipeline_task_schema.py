"""
Unit tests for pipeline/task_schema.py module.

Tests cover:
- Task model creation and validation
- Task status transitions
- Acceptance criteria
- Task dependencies
- Research findings
- File loading and saving
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pytest

from pipeline.task_schema import (
    AcceptanceCriterion,
    CodeReference,
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


class TestTaskPriority:
    """Test TaskPriority enum."""
    
    def test_task_priority_values(self):
        """Test task priority enum values."""
        assert TaskPriority.LOW.value == "low"
        assert TaskPriority.MEDIUM.value == "medium"
        assert TaskPriority.HIGH.value == "high"
        assert TaskPriority.CRITICAL.value == "critical"


class TestTaskStatus:
    """Test TaskStatus enum."""
    
    def test_task_status_values(self):
        """Test task status enum values."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"


class TestAcceptanceCriterion:
    """Test AcceptanceCriterion model."""
    
    def test_criterion_creation(self):
        """Test creating acceptance criterion."""
        criterion = AcceptanceCriterion(
            description="Must have unit tests",
        )
        
        assert criterion.description == "Must have unit tests"
        assert criterion.verified is False
        assert criterion.id is not None
    
    def test_criterion_validation(self):
        """Test criterion validation."""
        with pytest.raises(ValueError, match="Description must not be empty"):
            AcceptanceCriterion(description="   ")


class TestTaskDependency:
    """Test TaskDependency model."""
    
    def test_dependency_creation(self):
        """Test creating task dependency."""
        dep = TaskDependency(
            task_id="task-123",
            relationship="blocks",
            notes="Must be done first",
        )
        
        assert dep.task_id == "task-123"
        assert dep.relationship == "blocks"


class TestResearchFinding:
    """Test ResearchFinding model."""
    
    def test_research_finding_creation(self):
        """Test creating research finding."""
        finding = ResearchFinding(
            source="documentation",
            content="Found relevant info",
            url="https://example.com",
            relevance_score=0.9,
        )
        
        assert finding.source == "documentation"
        assert finding.relevance_score == 0.9


class TestCodeReference:
    """Test CodeReference model."""
    
    def test_code_reference_creation(self):
        """Test creating code reference."""
        ref = CodeReference(
            file_path="src/main.py",
            line_start=10,
            line_end=20,
            content="def main():",
            language="python",
        )
        
        assert ref.file_path == "src/main.py"
        assert ref.language == "python"


class TestImplementationNote:
    """Test ImplementationNote model."""
    
    def test_implementation_note_creation(self):
        """Test creating implementation note."""
        note = ImplementationNote(
            content="Use async/await pattern",
            author="ironclaw",
            priority=TaskPriority.HIGH,
        )
        
        assert note.content == "Use async/await pattern"
        assert note.priority == TaskPriority.HIGH


class TestTask:
    """Test Task model."""
    
    def test_task_creation(self):
        """Test creating a basic task."""
        task = Task(
            title="Implement feature",
            description="Add new authentication feature",
        )
        
        assert task.title == "Implement feature"
        assert task.status == TaskStatus.PENDING
        assert task.priority == TaskPriority.MEDIUM
        assert task.id is not None
    
    def test_task_validation_empty_title(self):
        """Test task validation with empty title."""
        with pytest.raises(ValueError, match="Title must not be empty"):
            Task(title="   ", description="Description")
    
    def test_task_validation_empty_description(self):
        """Test task validation with empty description."""
        with pytest.raises(ValueError, match="Description must not be empty"):
            Task(title="Title", description="   ")
    
    def test_task_start(self):
        """Test starting a task."""
        task = Task(title="Task", description="Description")
        
        task.start(assigned_to="aider")
        
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.assigned_to == "aider"
        assert task.started_at is not None
    
    def test_task_complete(self):
        """Test completing a task."""
        task = Task(title="Task", description="Description")
        task.start()
        
        task.complete(
            implementation_files=["src/main.py"],
            test_files=["tests/test_main.py"],
            notes="Done",
        )
        
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None
        assert "src/main.py" in task.implementation_files
    
    def test_task_fail(self):
        """Test failing a task."""
        task = Task(title="Task", description="Description")
        task.start()
        
        task.fail("Build failed")
        
        assert task.status == TaskStatus.FAILED
        assert task.error_message == "Build failed"
        assert task.completed_at is not None
    
    def test_task_cancel(self):
        """Test cancelling a task."""
        task = Task(title="Task", description="Description")
        
        task.cancel()
        
        assert task.status == TaskStatus.CANCELLED
    
    def test_task_add_research_finding(self):
        """Test adding research finding."""
        task = Task(title="Task", description="Description")
        
        finding = ResearchFinding(
            source="docs",
            content="Info",
        )
        task.add_research_finding(finding)
        
        assert len(task.research_findings) == 1
    
    def test_task_add_implementation_note(self):
        """Test adding implementation note."""
        task = Task(title="Task", description="Description")
        
        task.add_implementation_note("Use fast algorithms")
        
        assert len(task.implementation_notes) == 1
    
    def test_task_add_acceptance_criterion(self):
        """Test adding acceptance criterion."""
        task = Task(title="Task", description="Description")
        
        criterion_id = task.add_acceptance_criterion("Must have tests")
        
        assert len(task.acceptance_criteria) == 1
        assert isinstance(criterion_id, str)
    
    def test_task_verify_criterion(self):
        """Test verifying acceptance criterion."""
        task = Task(title="Task", description="Description")
        criterion_id = task.add_acceptance_criterion("Must have tests")
        
        result = task.verify_criterion(criterion_id, notes="Tests added")
        
        assert result is True
        assert task.acceptance_criteria[0].verified is True
    
    def test_task_verify_nonexistent_criterion(self):
        """Test verifying non-existent criterion."""
        task = Task(title="Task", description="Description")
        
        result = task.verify_criterion("nonexistent")
        
        assert result is False
    
    def test_task_is_complete(self):
        """Test is_complete property."""
        task = Task(title="Task", description="Description")
        
        assert task.is_complete is False
        
        task.complete()
        assert task.is_complete is True
    
    def test_task_is_failed(self):
        """Test is_failed property."""
        task = Task(title="Task", description="Description")
        
        assert task.is_failed is False
        
        task.fail("Error")
        assert task.is_failed is True
    
    def test_task_all_criteria_met(self):
        """Test all_criteria_met property."""
        task = Task(title="Task", description="Description")
        
        # No criteria means all met
        assert task.all_criteria_met is True
        
        # Add criteria
        cid1 = task.add_acceptance_criterion("Criterion 1")
        cid2 = task.add_acceptance_criterion("Criterion 2")
        
        assert task.all_criteria_met is False
        
        # Verify one
        task.verify_criterion(cid1)
        assert task.all_criteria_met is False
        
        # Verify all
        task.verify_criterion(cid2)
        assert task.all_criteria_met is True
    
    def test_task_completion_percentage(self):
        """Test completion_percentage property."""
        task = Task(title="Task", description="Description")
        
        # No criteria, not completed
        assert task.completion_percentage == 0.0
        
        # No criteria, completed
        task.complete()
        assert task.completion_percentage == 100.0
        
        # With criteria
        task2 = Task(title="Task", description="Description")
        task2.add_acceptance_criterion("C1")
        task2.add_acceptance_criterion("C2")
        task2.add_acceptance_criterion("C3")
        
        assert task2.completion_percentage == 0.0
        
        # Verify one
        task2.verify_criterion(task2.acceptance_criteria[0].id)
        assert abs(task2.completion_percentage - 33.33) < 0.1


class TestTaskList:
    """Test TaskList model."""
    
    def test_task_list_creation(self):
        """Test creating task list."""
        task_list = TaskList()
        
        assert len(task_list.tasks) == 0
    
    def test_task_list_add_task(self):
        """Test adding task to list."""
        task_list = TaskList()
        task = Task(title="Task", description="Description")
        
        task_id = task_list.add_task(task)
        
        assert task_id == task.id
        assert len(task_list.tasks) == 1
    
    def test_task_list_get_task(self):
        """Test getting task from list."""
        task_list = TaskList()
        task = Task(title="Task", description="Description")
        task_list.add_task(task)
        
        retrieved = task_list.get_task(task.id)
        
        assert retrieved is not None
        assert retrieved.title == "Task"
    
    def test_task_list_get_nonexistent_task(self):
        """Test getting non-existent task from list."""
        task_list = TaskList()
        
        result = task_list.get_task("nonexistent")
        
        assert result is None
    
    def test_task_list_get_tasks_by_status(self):
        """Test getting tasks by status."""
        task_list = TaskList()
        
        task1 = Task(title="Task 1", description="Desc 1", status=TaskStatus.PENDING)
        task2 = Task(title="Task 2", description="Desc 2", status=TaskStatus.COMPLETED)
        task3 = Task(title="Task 3", description="Desc 3", status=TaskStatus.PENDING)
        
        task_list.add_task(task1)
        task_list.add_task(task2)
        task_list.add_task(task3)
        
        pending = task_list.get_tasks_by_status(TaskStatus.PENDING)
        
        assert len(pending) == 2
    
    def test_task_list_get_tasks_by_priority(self):
        """Test getting tasks by priority."""
        task_list = TaskList()
        
        task1 = Task(title="Task 1", description="Desc 1", priority=TaskPriority.HIGH)
        task2 = Task(title="Task 2", description="Desc 2", priority=TaskPriority.LOW)
        
        task_list.add_task(task1)
        task_list.add_task(task2)
        
        high_priority = task_list.get_tasks_by_priority(TaskPriority.HIGH)
        
        assert len(high_priority) == 1
    
    def test_task_list_counts(self):
        """Test task list count properties."""
        task_list = TaskList()
        
        task_list.add_task(Task(title="T1", description="D1", status=TaskStatus.PENDING))
        task_list.add_task(Task(title="T2", description="D2", status=TaskStatus.IN_PROGRESS))
        task_list.add_task(Task(title="T3", description="D3", status=TaskStatus.COMPLETED))
        task_list.add_task(Task(title="T4", description="D4", status=TaskStatus.FAILED))
        
        assert task_list.pending_count == 1
        assert task_list.in_progress_count == 1
        assert task_list.completed_count == 1
        assert task_list.failed_count == 1


class TestTaskFileOperations:
    """Test task file loading and saving."""
    
    def test_save_and_load_json(self):
        """Test saving and loading task as JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            task = Task(title="Test Task", description="Test Description")
            file_path = Path(tmpdir) / "task.json"
            
            save_task_to_file(task, file_path, format='json')
            
            assert file_path.exists()
            
            loaded = load_task_from_file(file_path)
            
            assert loaded.id == task.id
            assert loaded.title == "Test Task"
    
    def test_save_and_load_markdown(self):
        """Test saving and loading task as Markdown."""
        with tempfile.TemporaryDirectory() as tmpdir:
            task = Task(
                title="Test Task",
                description="Test Description",
                requirements=["Req 1", "Req 2"],
            )
            file_path = Path(tmpdir) / "task.md"
            
            save_task_to_file(task, file_path, format='markdown')
            
            assert file_path.exists()
            
            loaded = load_task_from_file(file_path)
            
            assert loaded.title == "Test Task"
    
    def test_load_nonexistent_file(self):
        """Test loading non-existent file."""
        with pytest.raises(FileNotFoundError):
            load_task_from_file(Path("/nonexistent/file.json"))
    
    def test_load_unsupported_format(self):
        """Test loading unsupported file format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "task.txt"
            file_path.write_text("some content")
            
            with pytest.raises(ValueError, match="Unsupported file format"):
                load_task_from_file(file_path)
    
    def test_save_unsupported_format(self):
        """Test saving to unsupported format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            task = Task(title="Test", description="Description")
            file_path = Path(tmpdir) / "task.txt"
            
            with pytest.raises(ValueError, match="Unsupported format"):
                save_task_to_file(task, file_path, format='txt')
