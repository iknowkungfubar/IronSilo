"""
Agent bridge service for Aider/IronClaw handoff pipeline.

This module provides HTTP service for inter-agent communication,
enabling task submission, status polling, and webhook notifications.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import structlog

from .task_schema import Task, TaskList, TaskPriority, TaskStatus, save_task_to_file

logger = structlog.get_logger(__name__)


class TaskSubmission(BaseModel):
    """Task submission request."""
    
    title: str
    description: str
    priority: TaskPriority = TaskPriority.MEDIUM
    requirements: List[str] = Field(default_factory=list)
    acceptance_criteria: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    estimated_effort: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskUpdate(BaseModel):
    """Task update request."""
    
    status: Optional[TaskStatus] = None
    assigned_to: Optional[str] = None
    result_notes: Optional[str] = None
    error_message: Optional[str] = None
    implementation_files: Optional[List[str]] = None
    test_files: Optional[List[str]] = None


class TaskResponse(BaseModel):
    """Task response."""
    
    task: Task
    message: str = "Success"


class TaskListResponse(BaseModel):
    """Task list response."""
    
    tasks: List[Task]
    total: int
    page: int
    page_size: int


class WebhookRegistration(BaseModel):
    """Webhook registration request."""
    
    url: str
    events: List[str] = Field(default=["task.completed", "task.failed"])
    secret: Optional[str] = None


class Database:
    """SQLite database for task persistence."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    task_json TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at)
            """)
            conn.commit()
    
    def save_task(self, task: Task) -> None:
        """Save or update a task."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO tasks (id, title, status, priority, created_at, updated_at, task_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.id,
                    task.title,
                    task.status.value,
                    task.priority.value,
                    task.created_at.isoformat(),
                    task.updated_at.isoformat(),
                    task.model_dump_json(),
                ),
            )
            conn.commit()
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT task_json FROM tasks WHERE id = ?",
                (task_id,),
            )
            row = cursor.fetchone()
            if row:
                return Task.model_validate_json(row[0])
        return None
    
    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[Task], int]:
        """List tasks with optional filtering."""
        with sqlite3.connect(self.db_path) as conn:
            # Build query
            query = "SELECT task_json FROM tasks"
            conditions = []
            params = []
            
            if status:
                conditions.append("status = ?")
                params.append(status.value)
            
            if priority:
                conditions.append("priority = ?")
                params.append(priority.value)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            # Get total count
            count_query = query.replace("SELECT task_json", "SELECT COUNT(*)")
            cursor = conn.execute(count_query, params)
            total = cursor.fetchone()[0]
            
            # Get paginated results
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([page_size, (page - 1) * page_size])
            
            cursor = conn.execute(query, params)
            tasks = [Task.model_validate_json(row[0]) for row in cursor.fetchall()]
            
            return tasks, total
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            return cursor.rowcount > 0


class AgentBridge:
    """
    HTTP service for agent-to-agent communication.
    
    Provides REST API for task submission, status polling, and webhooks.
    """
    
    def __init__(
        self,
        workspace_dir: Path,
        db_path: Optional[Path] = None,
        host: str = "0.0.0.0",
        port: int = 8090,
    ):
        self.workspace_dir = Path(workspace_dir)
        self.db_path = db_path or self.workspace_dir / "tasks.db"
        self.host = host
        self.port = port
        
        self.db = Database(self.db_path)
        self.webhooks: List[WebhookRegistration] = []
        self.websocket_clients: List[WebSocket] = []
        
        self.app = self._create_app()
    
    def _create_app(self) -> FastAPI:
        """Create FastAPI application."""
        
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            logger.info("Starting Agent Bridge", workspace_dir=str(self.workspace_dir))
            yield
            # Shutdown
            logger.info("Shutting down Agent Bridge")
        
        app = FastAPI(
            title="IronSilo Agent Bridge",
            description="HTTP service for agent-to-agent task handoff",
            version="1.0.0",
            lifespan=lifespan,
        )
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Add routes
        self._add_routes(app)
        
        return app
    
    def _add_routes(self, app: FastAPI) -> None:
        """Add API routes."""
        
        @app.get("/health")
        async def health():
            """Health check endpoint."""
            return {"status": "healthy", "service": "agent-bridge"}
        
        @app.post("/tasks", response_model=TaskResponse, status_code=201)
        async def create_task(submission: TaskSubmission):
            """Create a new task."""
            # Create task
            task = Task(
                title=submission.title,
                description=submission.description,
                priority=submission.priority,
                requirements=submission.requirements,
                tags=submission.tags,
                estimated_effort=submission.estimated_effort,
                metadata=submission.metadata,
            )
            
            # Add acceptance criteria
            for criterion in submission.acceptance_criteria:
                task.add_acceptance_criterion(criterion)
            
            # Save to database
            self.db.save_task(task)
            
            # Save to file
            task_file = save_task_to_file(
                task,
                self.workspace_dir / f"TASK_{task.id[:8]}.json",
                format='json',
            )
            
            logger.info(
                "Task created",
                task_id=task.id,
                title=task.title,
                file_path=str(task_file),
            )
            
            # Notify webhooks
            await self._notify_webhooks("task.created", task)
            
            # Notify WebSocket clients
            await self._broadcast_websocket({
                "event": "task.created",
                "task_id": task.id,
                "task": task.model_dump(),
            })
            
            return TaskResponse(
                task=task,
                message=f"Task created successfully: {task.id}",
            )
        
        @app.get("/tasks/{task_id}", response_model=TaskResponse)
        async def get_task(task_id: str):
            """Get a task by ID."""
            task = self.db.get_task(task_id)
            if not task:
                raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
            
            return TaskResponse(task=task)
        
        @app.get("/tasks", response_model=TaskListResponse)
        async def list_tasks(
            status: Optional[TaskStatus] = None,
            priority: Optional[TaskPriority] = None,
            page: int = Query(1, ge=1),
            page_size: int = Query(20, ge=1, le=100),
        ):
            """List tasks with optional filtering."""
            tasks, total = self.db.list_tasks(status, priority, page, page_size)
            
            return TaskListResponse(
                tasks=tasks,
                total=total,
                page=page,
                page_size=page_size,
            )
        
        @app.put("/tasks/{task_id}", response_model=TaskResponse)
        async def update_task(task_id: str, update: TaskUpdate):
            """Update a task."""
            task = self.db.get_task(task_id)
            if not task:
                raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
            
            # Apply updates
            if update.status:
                if update.status == TaskStatus.IN_PROGRESS:
                    task.start()
                elif update.status == TaskStatus.COMPLETED:
                    task.complete(
                        implementation_files=update.implementation_files,
                        test_files=update.test_files,
                        notes=update.result_notes,
                    )
                elif update.status == TaskStatus.FAILED:
                    task.fail(update.error_message or "Task failed")
            
            if update.assigned_to:
                task.assigned_to = update.assigned_to
            
            if update.result_notes:
                task.result_notes = update.result_notes
            
            if update.error_message:
                task.error_message = update.error_message
            
            # Save updates
            self.db.save_task(task)
            
            # Update file
            task_file = self.workspace_dir / f"TASK_{task.id[:8]}.json"
            if task_file.exists():
                save_task_to_file(task, task_file, format='json')
            
            logger.info(
                "Task updated",
                task_id=task.id,
                new_status=task.status.value,
            )
            
            # Notify webhooks
            event = f"task.{task.status.value}"
            await self._notify_webhooks(event, task)
            
            # Notify WebSocket clients
            await self._broadcast_websocket({
                "event": event,
                "task_id": task.id,
                "task": task.model_dump(),
            })
            
            return TaskResponse(task=task)
        
        @app.post("/tasks/{task_id}/complete", response_model=TaskResponse)
        async def complete_task(
            task_id: str,
            implementation_files: Optional[List[str]] = None,
            test_files: Optional[List[str]] = None,
            notes: Optional[str] = None,
        ):
            """Mark a task as completed."""
            task = self.db.get_task(task_id)
            if not task:
                raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
            
            task.complete(
                implementation_files=implementation_files,
                test_files=test_files,
                notes=notes,
            )
            
            self.db.save_task(task)
            
            # Update file
            task_file = self.workspace_dir / f"TASK_{task.id[:8]}.json"
            if task_file.exists():
                save_task_to_file(task, task_file, format='json')
            
            logger.info("Task completed", task_id=task.id)
            
            await self._notify_webhooks("task.completed", task)
            await self._broadcast_websocket({
                "event": "task.completed",
                "task_id": task.id,
                "task": task.model_dump(),
            })
            
            return TaskResponse(task=task)
        
        @app.post("/tasks/{task_id}/fail", response_model=TaskResponse)
        async def fail_task(task_id: str, error_message: str):
            """Mark a task as failed."""
            task = self.db.get_task(task_id)
            if not task:
                raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
            
            task.fail(error_message)
            self.db.save_task(task)
            
            logger.info("Task failed", task_id=task.id, error=error_message)
            
            await self._notify_webhooks("task.failed", task)
            await self._broadcast_websocket({
                "event": "task.failed",
                "task_id": task.id,
                "task": task.model_dump(),
            })
            
            return TaskResponse(task=task)
        
        @app.delete("/tasks/{task_id}")
        async def delete_task(task_id: str):
            """Delete a task."""
            task = self.db.get_task(task_id)
            if not task:
                raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
            
            # Delete from database
            self.db.delete_task(task_id)
            
            # Delete file
            task_file = self.workspace_dir / f"TASK_{task.id[:8]}.json"
            if task_file.exists():
                task_file.unlink()
            
            logger.info("Task deleted", task_id=task_id)
            
            return {"message": f"Task {task_id} deleted"}
        
        @app.post("/webhooks", status_code=201)
        async def register_webhook(webhook: WebhookRegistration):
            """Register a webhook for task events."""
            self.webhooks.append(webhook)
            
            logger.info(
                "Webhook registered",
                url=webhook.url,
                events=webhook.events,
            )
            
            return {"message": "Webhook registered", "url": webhook.url}
        
        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates."""
            await websocket.accept()
            self.websocket_clients.append(websocket)
            
            try:
                while True:
                    # Keep connection alive
                    await websocket.receive_text()
            except WebSocketDisconnect:
                self.websocket_clients.remove(websocket)
    
    async def _notify_webhooks(self, event: str, task: Task) -> None:
        """Notify registered webhooks of task events."""
        import httpx
        
        for webhook in self.webhooks:
            if event in webhook.events or "*" in webhook.events:
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            webhook.url,
                            json={
                                "event": event,
                                "task_id": task.id,
                                "task": task.model_dump(),
                            },
                            timeout=10.0,
                        )
                        logger.info(
                            "Webhook notified",
                            url=webhook.url,
                            event=event,
                            status_code=response.status_code,
                        )
                except Exception as e:
                    logger.error(
                        "Webhook notification failed",
                        url=webhook.url,
                        error=str(e),
                    )
    
    async def _broadcast_websocket(self, data: Dict[str, Any]) -> None:
        """Broadcast message to all WebSocket clients."""
        disconnected = []
        
        for client in self.websocket_clients:
            try:
                await client.send_json(data)
            except Exception:
                disconnected.append(client)
        
        for client in disconnected:
            self.websocket_clients.remove(client)


def create_agent_bridge(
    workspace_dir: Path,
    db_path: Optional[Path] = None,
) -> AgentBridge:
    """Create an Agent Bridge instance."""
    return AgentBridge(workspace_dir=workspace_dir, db_path=db_path)


# For uvicorn
def get_app():
    """Get FastAPI app for uvicorn."""
    bridge = create_agent_bridge(Path.cwd())
    return bridge.app


app = get_app()
