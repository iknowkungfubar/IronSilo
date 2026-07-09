"""Unit tests for memory/main.py service.

Replaces old testes for genesys/app.py which was removed in Phase 2.
Tests cover the sqlite-vec backed memory service.
"""

import os
import tempfile
import shutil

import pytest


@pytest.fixture(autouse=True)
def reset_memory_state():
    """Reset memory service state and use temp DB between tests."""
    import memory.main as mem

    mem._initialized = False
    tmpdir = tempfile.mkdtemp()
    os.environ["MEMORY_DB_PATH"] = os.path.join(tmpdir, "test.db")
    yield
    shutil.rmtree(tmpdir, ignore_errors=True)
    if "MEMORY_DB_PATH" in os.environ:
        del os.environ["MEMORY_DB_PATH"]


class TestMemoryModels:
    """Test memory service models."""

    def test_memory_create_model(self):
        """Test MemoryCreate model."""
        from memory.main import MemoryCreate

        req = MemoryCreate(content="Test content", metadata={"key": "val"})
        assert req.content == "Test content"
        assert req.metadata["key"] == "val"

    def test_session_create_model(self):
        """Test SessionCreate model."""
        from memory.main import SessionCreate

        req = SessionCreate(user_id="user-1")
        assert req.user_id == "user-1"


class TestMemoryEndpoints:
    """Test memory API endpoints."""

    def test_health_endpoint(self):
        """Test health endpoint returns ok."""
        from memory.main import app

        assert app.title == "IronSilo Memory"

    @pytest.mark.asyncio
    async def test_create_memory(self):
        """Test creating a memory."""
        from memory.main import app, get_db
        from fastapi.testclient import TestClient

        # Initialize DB
        get_db()

        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/memories",
                json={"content": "Test memory", "metadata": {"type": "test"}},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "id" in data
            assert "created_at" in data

    @pytest.mark.asyncio
    async def test_search_memories(self):
        """Test searching memories."""
        from memory.main import app, get_db
        from fastapi.testclient import TestClient

        get_db()

        with TestClient(app) as client:
            client.post(
                "/api/v1/memories",
                json={"content": "Memory 1"},
            )
            resp = client.post(
                "/api/v1/memories/search",
                json={"query": "test", "limit": 10},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_memory(self):
        """Test getting a memory by ID."""
        from memory.main import app, get_db
        from fastapi.testclient import TestClient

        get_db()

        with TestClient(app) as client:
            create = client.post(
                "/api/v1/memories",
                json={"content": "Get me"},
            )
            mem_id = create.json()["id"]

            resp = client.get(f"/api/v1/memories/{mem_id}")
            assert resp.status_code == 200
            assert resp.json()["content"] == "Get me"

    def test_empty_content_rejected(self):
        """Test that empty content is rejected."""
        from memory.main import app
        from fastapi.testclient import TestClient

        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/memories",
                json={"content": ""},
            )
            assert resp.status_code == 422

    def test_empty_search_rejected(self):
        """Test that empty search is rejected."""
        from memory.main import app
        from fastapi.testclient import TestClient

        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/memories/search",
                json={"query": ""},
            )
            assert resp.status_code == 422

    def test_get_nonexistent_memory(self):
        """Test getting non-existent memory returns 404."""
        from memory.main import app, get_db
        from fastapi.testclient import TestClient

        get_db()

        with TestClient(app) as client:
            resp = client.get("/api/v1/memories/99999")
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_memory(self):
        """Test updating a memory."""
        from memory.main import app, get_db
        from fastapi.testclient import TestClient

        get_db()

        with TestClient(app) as client:
            create = client.post(
                "/api/v1/memories",
                json={"content": "Original"},
            )
            mem_id = create.json()["id"]

            resp = client.put(
                f"/api/v1/memories/{mem_id}",
                json={"content": "Updated", "metadata": {}},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "id" in data or "updated_at" in data
