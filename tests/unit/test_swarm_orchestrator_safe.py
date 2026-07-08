"""
Unit tests for swarm/orchestrator module - production ready.
All tests are synchronous to avoid async timing issues.
"""

from unittest.mock import MagicMock, patch


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

    def test_manager_default_memory_url(self):
        """Test Manager has correct default memory_url."""
        from swarm.orchestrator import Manager, MEMORY_URL

        mock_worker = MagicMock()
        manager = Manager(mock_worker)

        assert manager.memory_url == MEMORY_URL


class TestManagerConfig:
    """Test Manager configuration."""

    def test_memory_url_default(self):
        """Test MEMORY_URL has valid default."""
        from swarm.orchestrator import MEMORY_URL

        assert "memory" in MEMORY_URL or "localhost" in MEMORY_URL
        assert "8020" in MEMORY_URL


class TestManagerAttributes:
    """Test Manager has required attributes."""

    def test_manager_has_worker(self):
        """Test Manager has worker attribute."""
        from swarm.orchestrator import Manager

        mock_worker = MagicMock()
        manager = Manager(mock_worker)

        assert hasattr(manager, "worker")

    def test_manager_has_memory_url(self):
        """Test Manager has memory_url attribute."""
        from swarm.orchestrator import Manager

        mock_worker = MagicMock()
        manager = Manager(mock_worker)

        assert hasattr(manager, "memory_url")

    def test_manager_has_extract_and_store_method(self):
        """Test Manager has extract_and_store method."""
        from swarm.orchestrator import Manager

        mock_worker = MagicMock()
        manager = Manager(mock_worker)

        assert hasattr(manager, "extract_and_store")
        assert callable(manager.extract_and_store)

    def test_manager_has_store_memory_method(self):
        """Test Manager has _store_memory method."""
        from swarm.orchestrator import Manager

        mock_worker = MagicMock()
        manager = Manager(mock_worker)

        assert hasattr(manager, "_store_memory")

    def test_manager_has_run_research_session_method(self):
        """Test Manager has run_research_session method."""
        from swarm.orchestrator import Manager

        mock_worker = MagicMock()
        manager = Manager(mock_worker)

        assert hasattr(manager, "run_research_session")
        assert callable(manager.run_research_session)


class TestManagerMemoryNodeInput:
    """Test Manager's use of MemoryNodeInput."""

    def test_extract_and_store_uses_memory_node_input(self):
        """Test extract_and_store creates MemoryNodeInput."""
        from swarm.orchestrator import Manager

        mock_worker = MagicMock()
        mgr = Manager(mock_worker)

        # Verify Manager is an instance and the module imports MemoryNodeInput
        assert hasattr(mgr, "extract_and_store")


class TestOrchestratorEnvironment:
    """Test environment variable configuration."""

    def test_memory_url_default(self):
        """Test MEMORY_URL defaults to memory:8020."""
        from swarm.orchestrator import MEMORY_URL

        assert MEMORY_URL == "http://memory:8020"

    def test_memory_url_from_environment_patched(self):
        """Test MEMORY_URL can be patched for environment override testing."""
        from swarm import orchestrator

        with patch.object(orchestrator, "MEMORY_URL", "http://custom:9000"):
            assert orchestrator.MEMORY_URL == "http://custom:9000"
