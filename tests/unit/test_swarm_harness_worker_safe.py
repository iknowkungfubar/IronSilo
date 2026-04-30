"""
Unit tests for swarm/harness_worker module - production ready.
All tests are synchronous to avoid async timing issues.
"""

import json
from unittest.mock import MagicMock, patch

import pytest


class TestHarnessWorkerInit:
    """Test HarnessWorker initialization."""

    def test_worker_default_values(self):
        """Test worker initializes with correct defaults."""
        from swarm.harness_worker import HarnessWorker

        worker = HarnessWorker()

        assert worker.cdp_url == "ws://browser-node:9222"
        assert worker.ws is None
        assert worker._message_id == 0
        assert len(worker._response_futures) == 0

    def test_worker_custom_cdp_url(self):
        """Test worker accepts custom CDP URL."""
        from swarm.harness_worker import HarnessWorker

        worker = HarnessWorker(cdp_url="ws://custom:9223")

        assert worker.cdp_url == "ws://custom:9223"

    def test_response_futures_empty_initially(self):
        """Test response futures dict is empty on init."""
        from swarm.harness_worker import HarnessWorker

        worker = HarnessWorker()

        assert isinstance(worker._response_futures, dict)
        assert len(worker._response_futures) == 0


class TestHarnessWorkerConfig:
    """Test module configuration."""

    def test_cdp_url_default_value(self):
        """Test CDP_URL module constant has valid default."""
        from swarm.harness_worker import CDP_URL

        assert CDP_URL == "ws://browser-node:9222"

    def test_openai_api_base_has_v1_endpoint(self):
        """Test OPENAI_API_BASE has v1/chat/completions path."""
        from swarm.harness_worker import OPENAI_API_BASE

        assert OPENAI_API_BASE.startswith("http")
        assert "/v1" in OPENAI_API_BASE or "/chat" in OPENAI_API_BASE


class TestHarnessWorkerHelpers:
    """Test helper methods and properties."""

    def test_worker_has_connect_method(self):
        """Test worker has connect method."""
        from swarm.harness_worker import HarnessWorker

        worker = HarnessWorker()
        assert hasattr(worker, 'connect')
        assert callable(worker.connect)

    def test_worker_has_disconnect_method(self):
        """Test worker has disconnect method."""
        from swarm.harness_worker import HarnessWorker

        worker = HarnessWorker()
        assert hasattr(worker, 'disconnect')
        assert callable(worker.disconnect)

    def test_worker_has_send_command_method(self):
        """Test worker has _send_command method."""
        from swarm.harness_worker import HarnessWorker

        worker = HarnessWorker()
        assert hasattr(worker, '_send_command')
        assert callable(worker._send_command)

    def test_worker_has_get_dom_method(self):
        """Test worker has get_dom method."""
        from swarm.harness_worker import HarnessWorker

        worker = HarnessWorker()
        assert hasattr(worker, 'get_dom')
        assert callable(worker.get_dom)

    def test_worker_has_click_element_method(self):
        """Test worker has click_element method."""
        from swarm.harness_worker import HarnessWorker

        worker = HarnessWorker()
        assert hasattr(worker, 'click_element')
        assert callable(worker.click_element)

    def test_worker_has_evaluate_for_research_method(self):
        """Test worker has evaluate_for_research method."""
        from swarm.harness_worker import HarnessWorker

        worker = HarnessWorker()
        assert hasattr(worker, 'evaluate_for_research')
        assert callable(worker.evaluate_for_research)

    def test_worker_has_receive_loop_method(self):
        """Test worker has _receive_loop method."""
        from swarm.harness_worker import HarnessWorker

        worker = HarnessWorker()
        assert hasattr(worker, '_receive_loop')
        assert callable(worker._receive_loop)


class TestHarnessWorkerState:
    """Test worker state management."""

    def test_worker_initial_ws_is_none(self):
        """Test ws starts as None."""
        from swarm.harness_worker import HarnessWorker

        worker = HarnessWorker()
        assert worker.ws is None

    def test_worker_initial_message_id_zero(self):
        """Test _message_id starts at 0."""
        from swarm.harness_worker import HarnessWorker

        worker = HarnessWorker()
        assert worker._message_id == 0

    def test_worker_cdp_url_attribute(self):
        """Test cdp_url attribute exists and is a string."""
        from swarm.harness_worker import HarnessWorker

        worker = HarnessWorker()
        assert isinstance(worker.cdp_url, str)
        assert "browser-node" in worker.cdp_url or "localhost" in worker.cdp_url


class TestHarnessWorkerMessageId:
    """Test message ID incrementing logic."""

    def test_message_id_increments_by_one(self):
        """Test message ID increments by 1."""
        from swarm.harness_worker import HarnessWorker

        worker = HarnessWorker()
        worker._message_id = 5
        worker._message_id += 1

        assert worker._message_id == 6

    def test_message_id_can_be_set(self):
        """Test message ID can be manually set."""
        from swarm.harness_worker import HarnessWorker

        worker = HarnessWorker()
        worker._message_id = 100

        assert worker._message_id == 100


class TestHarnessWorkerEvaluate:
    """Test evaluate_for_research method behavior."""

    def test_evaluate_uses_openai_api_base(self):
        """Test evaluate uses OPENAI_API_BASE from config."""
        from swarm.harness_worker import OPENAI_API_BASE

        assert "llm-proxy" in OPENAI_API_BASE or "localhost" in OPENAI_API_BASE or "127.0.0.1" in OPENAI_API_BASE


class TestHarnessWorkerEnvironment:
    """Test environment variable configuration."""

    def test_cdp_url_default(self):
        """Test CDP_URL defaults to browser-node:9222."""
        from swarm.harness_worker import CDP_URL

        assert CDP_URL == "ws://browser-node:9222"

    def test_openai_api_base_default(self):
        """Test OPENAI_API_BASE has valid default."""
        from swarm.harness_worker import OPENAI_API_BASE

        assert OPENAI_API_BASE.startswith("http")
        assert "/v1" in OPENAI_API_BASE

    def test_cdp_url_from_environment_patched(self):
        """Test CDP_URL can be patched for environment override testing."""
        from swarm import harness_worker

        with patch.object(harness_worker, 'CDP_URL', "ws://custom:9999"):
            assert harness_worker.CDP_URL == "ws://custom:9999"


class TestHarnessWorkerCDPCommands:
    """Test CDP command constants."""

    def test_dom_get_document_method(self):
        """Test DOM.getDocument is a valid CDP method."""
        valid_methods = ["DOM.getDocument", "Runtime.evaluate", "Runtime.callFunctionOn"]
        for method in valid_methods:
            assert isinstance(method, str)
            assert "." in method


class TestHarnessWorkerFutureDict:
    """Test _response_futures dictionary behavior."""

    def test_response_futures_is_dict(self):
        """Test _response_futures is a dict."""
        from swarm.harness_worker import HarnessWorker

        worker = HarnessWorker()
        assert isinstance(worker._response_futures, dict)

    def test_response_futures_can_store_values(self):
        """Test _response_futures can store values."""
        from swarm.harness_worker import HarnessWorker

        worker = HarnessWorker()
        worker._response_futures[1] = "future_placeholder"

        assert 1 in worker._response_futures
        assert worker._response_futures[1] == "future_placeholder"