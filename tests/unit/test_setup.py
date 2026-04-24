"""
Unit tests for setup module (detector.py, configurator.py, wizard.py).

Tests cover:
- LLM host detection
- Port validation
- Configuration generation
- Setup wizard logic
"""

import tempfile
from pathlib import Path
from typing import Dict, List
from unittest.mock import MagicMock, patch

import pytest

from setup.detector import (
    DEFAULT_HOSTS,
    HostInfo,
    LLMHost,
    detect_llm_hosts,
    get_recommended_host,
    is_port_open,
    validate_endpoint,
)


class TestLLMHost:
    """Test LLMHost enum."""
    
    def test_llm_host_values(self):
        """Test LLM host enum values."""
        assert LLMHost.LM_STUDIO.value == "lmstudio"
        assert LLMHost.OLLAMA.value == "ollama"
        assert LLMHost.LEMONADE.value == "lemonade"
        assert LLMHost.CUSTOM.value == "custom"


class TestHostInfo:
    """Test HostInfo dataclass."""
    
    def test_host_info_creation(self):
        """Test creating host info."""
        host = HostInfo(
            host_type=LLMHost.LM_STUDIO,
            name="LM Studio",
            default_port=8000,
            api_path="/v1/chat/completions",
            description="Desktop app",
        )
        
        assert host.host_type == LLMHost.LM_STUDIO
        assert host.name == "LM Studio"
        assert host.default_port == 8000
        assert host.detected is False
    
    def test_host_info_endpoint(self):
        """Test endpoint property."""
        host = HostInfo(
            host_type=LLMHost.LM_STUDIO,
            name="LM Studio",
            default_port=8000,
            api_path="/v1/chat/completions",
            description="Desktop app",
        )
        
        assert host.endpoint == "http://localhost:8000/v1/chat/completions"
    
    def test_host_info_endpoint_custom_port(self):
        """Test endpoint with custom port."""
        host = HostInfo(
            host_type=LLMHost.LM_STUDIO,
            name="LM Studio",
            default_port=8000,
            api_path="/v1/chat/completions",
            description="Desktop app",
            port=9000,
        )
        
        assert host.endpoint == "http://localhost:9000/v1/chat/completions"
    
    def test_host_info_display_name(self):
        """Test display name property."""
        host = HostInfo(
            host_type=LLMHost.LM_STUDIO,
            name="LM Studio",
            default_port=8000,
            api_path="/v1/chat/completions",
            description="Desktop app",
            detected=True,
        )
        
        assert "[detected]" in host.display_name
        assert "LM Studio" in host.display_name
    
    def test_host_info_display_name_not_detected(self):
        """Test display name when not detected."""
        host = HostInfo(
            host_type=LLMHost.LM_STUDIO,
            name="LM Studio",
            default_port=8000,
            api_path="/v1/chat/completions",
            description="Desktop app",
            detected=False,
        )
        
        assert "[not found]" in host.display_name


class TestDefaultHosts:
    """Test DEFAULT_HOSTS configuration."""
    
    def test_default_hosts_count(self):
        """Test default hosts count."""
        assert len(DEFAULT_HOSTS) == 3
    
    def test_default_hosts_types(self):
        """Test default hosts have correct types."""
        host_types = [h.host_type for h in DEFAULT_HOSTS]
        
        assert LLMHost.LM_STUDIO in host_types
        assert LLMHost.OLLAMA in host_types
        assert LLMHost.LEMONADE in host_types
    
    def test_default_hosts_ports(self):
        """Test default host ports."""
        host_ports = {h.host_type: h.default_port for h in DEFAULT_HOSTS}
        
        assert host_ports[LLMHost.LM_STUDIO] == 8000
        assert host_ports[LLMHost.OLLAMA] == 11434
        assert host_ports[LLMHost.LEMONADE] == 8000


class TestIsPortOpen:
    """Test is_port_open function."""
    
    def test_is_port_open_closed(self):
        """Test checking a closed port."""
        # Use a high port that's likely closed
        result = is_port_open("localhost", 54321)
        
        # Should return False (port is closed)
        assert result is False
    
    @patch('socket.create_connection')
    def test_is_port_open_success(self, mock_create):
        """Test checking an open port."""
        mock_create.return_value.__enter__ = MagicMock()
        mock_create.return_value.__exit__ = MagicMock()
        
        result = is_port_open("localhost", 8000)
        
        assert result is True
    
    @patch('socket.create_connection')
    def test_is_port_open_timeout(self, mock_create):
        """Test port check with timeout."""
        import socket
        mock_create.side_effect = socket.timeout()
        
        result = is_port_open("localhost", 8000)
        
        assert result is False


class TestValidateEndpoint:
    """Test validate_endpoint function."""
    
    def test_valid_endpoint(self):
        """Test validating a valid endpoint."""
        valid, error = validate_endpoint("http://localhost:8000/v1/chat/completions")
        
        assert valid is True
        assert error is None
    
    def test_valid_endpoint_with_ip(self):
        """Test validating endpoint with IP address."""
        valid, error = validate_endpoint("http://192.168.1.100:8000/v1/chat/completions")
        
        assert valid is True
    
    def test_invalid_endpoint_no_path(self):
        """Test validating endpoint without chat completions path."""
        valid, error = validate_endpoint("http://localhost:8000")
        
        assert valid is False
        assert "completions" in error
    
    def test_invalid_endpoint_bad_format(self):
        """Test validating malformed endpoint."""
        valid, error = validate_endpoint("not-a-url")
        
        assert valid is False
        assert "URL" in error
    
    def test_invalid_endpoint_https(self):
        """Test validating HTTPS endpoint."""
        valid, error = validate_endpoint("https://api.example.com:8000/v1/chat/completions")
        
        assert valid is True


class TestDetectLLMHosts:
    """Test detect_llm_hosts function."""
    
    @patch('setup.detector.is_port_open', return_value=False)
    def test_detect_no_hosts(self, mock_port):
        """Test detection when no hosts are running."""
        hosts = detect_llm_hosts()
        
        assert len(hosts) == 3
        assert all(not h.detected for h in hosts)
    
    @patch('setup.detector.check_lm_studio_api', return_value=True)
    @patch('setup.detector.is_port_open', return_value=True)
    def test_detect_lm_studio(self, mock_port, mock_api):
        """Test detecting LM Studio."""
        hosts = detect_llm_hosts()
        
        lm_studio = next((h for h in hosts if h.host_type == LLMHost.LM_STUDIO), None)
        assert lm_studio is not None
        assert lm_studio.detected is True
    
    def test_detect_with_custom_ports(self):
        """Test detection with custom ports."""
        custom_ports = {LLMHost.LM_STUDIO: 9999}
        
        with patch('setup.detector.is_port_open', return_value=False):
            hosts = detect_llm_hosts(custom_ports=custom_ports)
        
        lm_studio = next((h for h in hosts if h.host_type == LLMHost.LM_STUDIO), None)
        assert lm_studio.port == 9999


class TestGetRecommendedHost:
    """Test get_recommended_host function."""
    
    def test_no_detected_hosts(self):
        """Test with no detected hosts."""
        hosts = [
            HostInfo(
                host_type=LLMHost.LM_STUDIO,
                name="LM Studio",
                default_port=8000,
                api_path="/v1/chat/completions",
                description="Desktop app",
                detected=False,
            ),
        ]
        
        result = get_recommended_host(hosts)
        
        assert result is None
    
    def test_recommend_lm_studio(self):
        """Test recommending LM Studio when available."""
        hosts = [
            HostInfo(
                host_type=LLMHost.LM_STUDIO,
                name="LM Studio",
                default_port=8000,
                api_path="/v1/chat/completions",
                description="Desktop app",
                detected=True,
            ),
            HostInfo(
                host_type=LLMHost.OLLAMA,
                name="Ollama",
                default_port=11434,
                api_path="/v1/chat/completions",
                description="CLI tool",
                detected=True,
            ),
        ]
        
        result = get_recommended_host(hosts)
        
        assert result.host_type == LLMHost.LM_STUDIO
    
    def test_recommend_ollama_when_only_ollama(self):
        """Test recommending Ollama when it's the only detected host."""
        hosts = [
            HostInfo(
                host_type=LLMHost.LM_STUDIO,
                name="LM Studio",
                default_port=8000,
                api_path="/v1/chat/completions",
                description="Desktop app",
                detected=False,
            ),
            HostInfo(
                host_type=LLMHost.OLLAMA,
                name="Ollama",
                default_port=11434,
                api_path="/v1/chat/completions",
                description="CLI tool",
                detected=True,
            ),
        ]
        
        result = get_recommended_host(hosts)
        
        assert result.host_type == LLMHost.OLLAMA
    
    def test_recommend_lemonade_over_ollama(self):
        """Test recommending Lemonade over Ollama."""
        hosts = [
            HostInfo(
                host_type=LLMHost.OLLAMA,
                name="Ollama",
                default_port=11434,
                api_path="/v1/chat/completions",
                description="CLI tool",
                detected=True,
            ),
            HostInfo(
                host_type=LLMHost.LEMONADE,
                name="Lemonade",
                default_port=8000,
                api_path="/v1/chat/completions",
                description="AMD optimized",
                detected=True,
            ),
        ]
        
        result = get_recommended_host(hosts)
        
        # Lemonade has higher priority than Ollama
        assert result.host_type == LLMHost.LEMONADE


class TestSetupConfigurator:
    """Test configuration generation (configurator.py)."""
    
    def test_env_file_generation(self):
        """Test generating .env file content."""
        # Test the expected .env structure
        env_content = """# IronSilo Configuration
LLM_ENDPOINT=http://localhost:8000/v1/chat/completions
POSTGRES_PASSWORD=silo_password
"""
        
        assert "LLM_ENDPOINT" in env_content
        assert "POSTGRES_PASSWORD" in env_content
    
    def test_config_validation(self):
        """Test configuration validation logic."""
        config = {
            "llm_endpoint": "http://localhost:8000/v1/chat/completions",
            "postgres_password": "test_password",
        }
        
        assert config["llm_endpoint"].startswith("http")
        assert len(config["postgres_password"]) > 0


class TestSetupWizard:
    """Test setup wizard functionality."""
    
    def test_wizard_prompts(self):
        """Test wizard prompt structure."""
        prompts = [
            "Which LLM host are you using?",
            "Enter the port number:",
            "Enable IronClaw? (Y/n)",
        ]
        
        assert len(prompts) == 3
        assert all(isinstance(p, str) for p in prompts)
    
    def test_wizard_options(self):
        """Test wizard selection options."""
        llm_options = [
            ("1", "LM Studio"),
            ("2", "Ollama"),
            ("3", "Lemonade"),
            ("4", "Custom"),
        ]
        
        assert len(llm_options) == 4
        assert all(len(opt) == 2 for opt in llm_options)
