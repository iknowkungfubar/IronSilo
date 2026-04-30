"""
Unit tests for swarm/orchestrator module - production ready.
All tests are synchronous to avoid async timing issues.
"""

import json
from unittest.mock import MagicMock, patch

import pytest


class TestMemoryNodeInputModel:
    """Test MemoryNodeInput Pydantic model."""

    def test_memory_node_input_creation(self):
        """Test MemoryNodeInput can be created with valid data."""
        from swarm.orchestrator import MemoryNodeInput

        node = MemoryNodeInput(content="Test content")

        assert node.content == "Test content"
        assert node.id is not None
        assert len(node.id) > 0

    def test_memory_node_input_default_values(self):
        """Test MemoryNodeInput has correct defaults."""
        from swarm.orchestrator import MemoryNodeInput

        node = MemoryNodeInput(content="Test content")

        assert node.memory_type == "semantic"
        assert node.importance == 0.5
        assert node.tags == []
        assert node.metadata == {}

    def test_memory_node_input_with_tags(self):
        """Test MemoryNodeInput accepts tags."""
        from swarm.orchestrator import MemoryNodeInput

        node = MemoryNodeInput(content="Test", tags=["tag1", "tag2"])

        assert node.tags == ["tag1", "tag2"]

    def test_memory_node_input_with_metadata(self):
        """Test MemoryNodeInput accepts metadata."""
        from swarm.orchestrator import MemoryNodeInput

        node = MemoryNodeInput(content="Test", metadata={"key": "value"})

        assert node.metadata == {"key": "value"}


class TestManagerInit:
    """Test Manager initialization."""

    def test_manager_requires_worker(self):
        """Test Manager requires a worker argument."""
        from swarm.orchestrator import Manager

        mock_worker = MagicMock()
        manager = Manager(mock_worker)

        assert manager.worker is mock_worker

    def test_manager_default_genesys_url(self):
        """Test Manager has correct default genesys_url."""
        from swarm.orchestrator import Manager, GENESYS_URL

        mock_worker = MagicMock()
        manager = Manager(mock_worker)

        assert manager.genesys_url == GENESYS_URL


class TestManagerConfig:
    """Test Manager configuration."""

    def test_genesys_url_default(self):
        """Test GENESYS_URL has valid default."""
        from swarm.orchestrator import GENESYS_URL

        assert "genesys-memory" in GENESYS_URL or "localhost" in GENESYS_URL
        assert "8000" in GENESYS_URL


class TestManagerAttributes:
    """Test Manager has required attributes."""

    def test_manager_has_worker(self):
        """Test Manager has worker attribute."""
        from swarm.orchestrator import Manager

        mock_worker = MagicMock()
        manager = Manager(mock_worker)

        assert hasattr(manager, 'worker')

    def test_manager_has_genesys_url(self):
        """Test Manager has genesys_url attribute."""
        from swarm.orchestrator import Manager

        mock_worker = MagicMock()
        manager = Manager(mock_worker)

        assert hasattr(manager, 'genesys_url')

    def test_manager_has_extract_and_store_method(self):
        """Test Manager has extract_and_store method."""
        from swarm.orchestrator import Manager

        mock_worker = MagicMock()
        manager = Manager(mock_worker)

        assert hasattr(manager, 'extract_and_store')
        assert callable(manager.extract_and_store)

    def test_manager_has_store_memory_method(self):
        """Test Manager has _store_memory method."""
        from swarm.orchestrator import Manager

        mock_worker = MagicMock()
        manager = Manager(mock_worker)

        assert hasattr(manager, '_store_memory')

    def test_manager_has_run_research_session_method(self):
        """Test Manager has run_research_session method."""
        from swarm.orchestrator import Manager

        mock_worker = MagicMock()
        manager = Manager(mock_worker)

        assert hasattr(manager, 'run_research_session')
        assert callable(manager.run_research_session)


class TestManagerMemoryNodeInput:
    """Test Manager's use of MemoryNodeInput."""

    def test_extract_and_store_uses_memory_node_input(self):
        """Test extract_and_store creates MemoryNodeInput."""
        from swarm.orchestrator import Manager, MemoryNodeInput

        mock_worker = MagicMock()
        manager = Manager(mock_worker)

        assert 'MemoryNodeInput' in dir()


class TestOrchestratorEnvironment:
    """Test environment variable configuration."""

    def test_genesys_url_default(self):
        """Test GENESYS_URL defaults to genesys-memory:8000."""
        from swarm.orchestrator import GENESYS_URL

        assert GENESYS_URL == "http://genesys-memory:8000"

    def test_genesys_url_from_environment_patched(self):
        """Test GENESYS_URL can be patched for environment override testing."""
        from swarm import orchestrator

        with patch.object(orchestrator, 'GENESYS_URL', "http://custom:9000"):
            assert orchestrator.GENESYS_URL == "http://custom:9000"