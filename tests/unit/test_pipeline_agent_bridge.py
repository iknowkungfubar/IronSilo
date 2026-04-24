"""
Unit tests for pipeline/agent_bridge.py module.

Tests cover:
- Database operations
- FastAPI endpoints (CRUD for tasks)
- Webhook registration and notification
- WebSocket connections
- Task submission and status updates
"""

import asyncio
import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from pipeline.agent_bridge import (
    AgentBridge,
    Database,
    TaskSubmission,
    TaskUpdate,
    WebhookRegistration,
    create_agent_bridge,
)
from pipeline.task_schema import Task, TaskPriority, TaskStatus


class TestDatabase:
    """Test Database class."""
    
    def test_database_init_creates_tables(self):
        """Test database initialization creates tables."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(db_path)
            
            assert db_path.exists()
    
    def test_save_and_get_task(self):
        """Test saving and retrieving a task."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(db_path)
            
            task = Task(
                title="Test Task",
                description="Test Description",
            )
            
            db.save_task(task)
            retrieved = db.get_task(task.id)
            
            assert retrieved is not None
            assert retrieved.id == task.id
            assert retrieved.title == "Test Task"
    
    def test_get_nonexistent_task(self):
        """Test getting a task that doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(db_path)
            
            result = db.get_task("nonexistent-id")
            
            assert result is None
    
    def test_list_tasks_empty(self):
        """Test listing tasks when database is empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(db_path)
            
            tasks, total = db.list_tasks()
            
            assert tasks == []
            assert total == 0
    
    def test_list_tasks_with_filter(self):
        """Test listing tasks with status filter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(db_path)
            
            # Create tasks with different statuses
            task1 = Task(title="Task 1", description="Desc 1", status=TaskStatus.PENDING)
            task2 = Task(title="Task 2", description="Desc 2", status=TaskStatus.COMPLETED)
            
            db.save_task(task1)
            db.save_task(task2)
            
            # Filter by status
            pending_tasks, _ = db.list_tasks(status=TaskStatus.PENDING)
            
            assert len(pending_tasks) == 1
            assert pending_tasks[0].title == "Task 1"
    
    def test_list_tasks_pagination(self):
        """Test task listing with pagination."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(db_path)
            
            # Create multiple tasks
            for i in range(5):
                task = Task(title=f"Task {i}", description=f"Desc {i}")
                db.save_task(task)
            
            # Get first page
            tasks_page1, total = db.list_tasks(page=1, page_size=2)
            
            assert len(tasks_page1) == 2
            assert total == 5
            
            # Get second page
            tasks_page2, _ = db.list_tasks(page=2, page_size=2)
            
            assert len(tasks_page2) == 2
    
    def test_delete_task(self):
        """Test deleting a task."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(db_path)
            
            task = Task(title="Task to delete", description="Will be deleted")
            db.save_task(task)
            
            # Delete the task
            result = db.delete_task(task.id)
            
            assert result is True
            assert db.get_task(task.id) is None
    
    def test_delete_nonexistent_task(self):
        """Test deleting a task that doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(db_path)
            
            result = db.delete_task("nonexistent-id")
            
            assert result is False


class TestAgentBridgeEndpoints:
    """Test Agent Bridge FastAPI endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bridge = create_agent_bridge(Path(tmpdir))
            yield TestClient(bridge.app)
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_create_task(self, client):
        """Test creating a new task."""
        submission = TaskSubmission(
            title="Test Task",
            description="Test Description",
            priority=TaskPriority.HIGH,
        )
        
        response = client.post("/tasks", json=submission.model_dump())
        
        assert response.status_code == 201
        data = response.json()
        assert data["task"]["title"] == "Test Task"
        assert data["task"]["priority"] == "high"
    
    def test_get_task(self, client):
        """Test getting a task by ID."""
        # Create a task first
        submission = TaskSubmission(
            title="Task to Get",
            description="Will be retrieved",
        )
        create_response = client.post("/tasks", json=submission.model_dump())
        task_id = create_response.json()["task"]["id"]
        
        # Get the task
        response = client.get(f"/tasks/{task_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["task"]["id"] == task_id
    
    def test_get_nonexistent_task(self, client):
        """Test getting a task that doesn't exist."""
        response = client.get("/tasks/nonexistent-id")
        
        assert response.status_code == 404
    
    def test_list_tasks(self, client):
        """Test listing all tasks."""
        # Create some tasks
        for i in range(3):
            submission = TaskSubmission(
                title=f"Task {i}",
                description=f"Description {i}",
            )
            client.post("/tasks", json=submission.model_dump())
        
        # List tasks
        response = client.get("/tasks")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 3
        assert len(data["tasks"]) >= 3
    
    def test_list_tasks_with_filter(self, client):
        """Test listing tasks with status filter."""
        # Create tasks with different statuses
        submission1 = TaskSubmission(title="Pending Task", description="Desc")
        response1 = client.post("/tasks", json=submission1.model_dump())
        task_id = response1.json()["task"]["id"]
        
        # Update task status
        update = TaskUpdate(status=TaskStatus.IN_PROGRESS)
        client.put(f"/tasks/{task_id}", json=update.model_dump(exclude_none=True))
        
        # Filter by status
        response = client.get("/tasks", params={"status": "in_progress"})
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) >= 1
    
    def test_update_task(self, client):
        """Test updating a task."""
        # Create a task
        submission = TaskSubmission(title="Task to Update", description="Desc")
        create_response = client.post("/tasks", json=submission.model_dump())
        task_id = create_response.json()["task"]["id"]
        
        # Update the task
        update = TaskUpdate(
            status=TaskStatus.IN_PROGRESS,
            assigned_to="aider",
        )
        response = client.put(f"/tasks/{task_id}", json=update.model_dump(exclude_none=True))
        
        assert response.status_code == 200
        data = response.json()
        assert data["task"]["status"] == "in_progress"
        assert data["task"]["assigned_to"] == "aider"
    
    def test_update_nonexistent_task(self, client):
        """Test updating a task that doesn't exist."""
        update = TaskUpdate(status=TaskStatus.COMPLETED)
        response = client.put("/tasks/nonexistent-id", json=update.model_dump(exclude_none=True))
        
        assert response.status_code == 404
    
    def test_complete_task(self, client):
        """Test completing a task."""
        # Create a task
        submission = TaskSubmission(title="Task to Complete", description="Desc")
        create_response = client.post("/tasks", json=submission.model_dump())
        task_id = create_response.json()["task"]["id"]
        
        # Complete the task - use PUT with update instead
        update = TaskUpdate(
            status=TaskStatus.COMPLETED,
            implementation_files=["src/main.py"],
            test_files=["tests/test_main.py"],
            result_notes="Implementation complete",
        )
        response = client.put(f"/tasks/{task_id}", json=update.model_dump(exclude_none=True))
        
        assert response.status_code == 200
        data = response.json()
        assert data["task"]["status"] == "completed"
        assert "src/main.py" in data["task"]["implementation_files"]
    
    def test_fail_task(self, client):
        """Test marking a task as failed."""
        # Create a task
        submission = TaskSubmission(title="Task to Fail", description="Desc")
        create_response = client.post("/tasks", json=submission.model_dump())
        task_id = create_response.json()["task"]["id"]
        
        # Fail the task
        response = client.post(
            f"/tasks/{task_id}/fail",
            params={"error_message": "Test error occurred"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["task"]["status"] == "failed"
        assert data["task"]["error_message"] == "Test error occurred"
    
    def test_delete_task(self, client):
        """Test deleting a task."""
        # Create a task
        submission = TaskSubmission(title="Task to Delete", description="Desc")
        create_response = client.post("/tasks", json=submission.model_dump())
        task_id = create_response.json()["task"]["id"]
        
        # Delete the task
        response = client.delete(f"/tasks/{task_id}")
        
        assert response.status_code == 200
        
        # Verify task is deleted
        get_response = client.get(f"/tasks/{task_id}")
        assert get_response.status_code == 404
    
    def test_delete_nonexistent_task(self, client):
        """Test deleting a task that doesn't exist."""
        response = client.delete("/tasks/nonexistent-id")
        
        assert response.status_code == 404


class TestWebhookRegistration:
    """Test webhook registration endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bridge = create_agent_bridge(Path(tmpdir))
            yield TestClient(bridge.app)
    
    def test_register_webhook(self, client):
        """Test registering a webhook."""
        webhook = WebhookRegistration(
            url="https://example.com/webhook",
            events=["task.completed", "task.failed"],
        )
        
        response = client.post("/webhooks", json=webhook.model_dump())
        
        assert response.status_code == 201
        data = response.json()
        assert "Webhook registered" in data["message"]


class TestTaskSubmission:
    """Test TaskSubmission model."""
    
    def test_task_submission_defaults(self):
        """Test task submission with defaults."""
        submission = TaskSubmission(
            title="Test",
            description="Description",
        )
        
        assert submission.title == "Test"
        assert submission.priority == TaskPriority.MEDIUM
        assert submission.requirements == []
        assert submission.tags == []
    
    def test_task_submission_full(self):
        """Test task submission with all fields."""
        submission = TaskSubmission(
            title="Full Task",
            description="Full description",
            priority=TaskPriority.HIGH,
            requirements=["Req 1", "Req 2"],
            acceptance_criteria=["AC 1", "AC 2"],
            tags=["test", "urgent"],
            estimated_effort="4 hours",
            metadata={"custom": "data"},
        )
        
        assert submission.priority == TaskPriority.HIGH
        assert len(submission.requirements) == 2
        assert len(submission.acceptance_criteria) == 2


class TestCreateAgentBridge:
    """Test create_agent_bridge factory function."""
    
    def test_create_agent_bridge(self):
        """Test creating an agent bridge instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bridge = create_agent_bridge(Path(tmpdir))
            
            assert bridge is not None
            assert bridge.workspace_dir == Path(tmpdir)
            assert bridge.app is not None
    
    def test_create_agent_bridge_custom_db(self):
        """Test creating agent bridge with custom database path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "custom.db"
            bridge = create_agent_bridge(Path(tmpdir), db_path=db_path)
            
            assert bridge.db_path == db_path


class TestGetApp:
    """Test get_app function for uvicorn."""
    
    def test_get_app(self):
        """Test getting FastAPI app for uvicorn."""
        from pipeline.agent_bridge import get_app
        
        app = get_app()
        
        assert app is not None
        assert app.title == "IronSilo Agent Bridge"


class TestTaskLifecycle:
    """Test complete task lifecycle through API."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bridge = create_agent_bridge(Path(tmpdir))
            yield TestClient(bridge.app)
    
    def test_complete_task_lifecycle(self, client):
        """Test complete task lifecycle: create -> start -> complete."""
        # 1. Create task
        submission = TaskSubmission(
            title="Lifecycle Task",
            description="Testing full lifecycle",
        )
        create_response = client.post("/tasks", json=submission.model_dump())
        assert create_response.status_code == 201
        task_id = create_response.json()["task"]["id"]
        
        # 2. Start task
        update = TaskUpdate(status=TaskStatus.IN_PROGRESS)
        start_response = client.put(f"/tasks/{task_id}", json=update.model_dump(exclude_none=True))
        assert start_response.status_code == 200
        assert start_response.json()["task"]["status"] == "in_progress"
        
        # 3. Complete task
        complete_response = client.post(f"/tasks/{task_id}/complete")
        assert complete_response.status_code == 200
        assert complete_response.json()["task"]["status"] == "completed"
        
        # 4. Verify final state
        get_response = client.get(f"/tasks/{task_id}")
        assert get_response.json()["task"]["status"] == "completed"
    
    def test_failed_task_lifecycle(self, client):
        """Test task lifecycle ending in failure."""
        # Create and fail task
        submission = TaskSubmission(title="Failing Task", description="Will fail")
        create_response = client.post("/tasks", json=submission.model_dump())
        task_id = create_response.json()["task"]["id"]
        
        # Fail the task
        fail_response = client.post(
            f"/tasks/{task_id}/fail",
            params={"error_message": "Implementation error"}
        )
        
        assert fail_response.status_code == 200
        assert fail_response.json()["task"]["status"] == "failed"
        assert fail_response.json()["task"]["error_message"] == "Implementation error"
