"""
Unit tests for setup/detector.py.

Tests cover:
- LLMHost enum
- HostInfo dataclass
- Port checking functions
- API checking functions
- Host detection
- Endpoint validation
"""

import socket
from unittest.mock import MagicMock, patch

import pytest

from setup.detector import (
    DEFAULT_HOSTS,
    HostInfo,
    LLMHost,
    check_lemonade_api,
    check_lm_studio_api,
    check_ollama_api,
    detect_llm_hosts,
    get_recommended_host,
    is_port_open,
    validate_endpoint,
)


class TestLLMHost:
    """Test LLMHost enum."""
    
    def test_llm_host_values(self):
        """Test LLMHost enum values."""
        assert LLMHost.LM_STUDIO.value == "lmstudio"
        assert LLMHost.OLLAMA.value == "ollama"
        assert LLMHost.LEMONADE.value == "lemonade"
        assert LLMHost.CUSTOM.value == "custom"
    
    def test_llm_host_is_string(self):
        """Test that LLMHost is a string enum."""
        assert isinstance(LLMHost.LM_STUDIO, str)
        assert LLMHost.LM_STUDIO == "lmstudio"


class TestHostInfo:
    """Test HostInfo dataclass."""
    
    def test_host_info_creation(self):
        """Test creating HostInfo."""
        host = HostInfo(
            host_type=LLMHost.OLLAMA,
            name="Ollama",
            default_port=11434,
            api_path="/v1/chat/completions",
            description="Test description",
        )
        
        assert host.host_type == LLMHost.OLLAMA
        assert host.name == "Ollama"
        assert host.default_port == 11434
        assert host.detected is False
        assert host.port is None
        assert host.version is None
    
    def test_host_info_endpoint(self):
        """Test HostInfo endpoint property."""
        host = HostInfo(
            host_type=LLMHost.OLLAMA,
            name="Ollama",
            default_port=11434,
            api_path="/v1/chat/completions",
            description="Test",
        )
        
        assert host.endpoint == "http://localhost:11434/v1/chat/completions"
    
    def test_host_info_endpoint_with_custom_port(self):
        """Test HostInfo endpoint with custom port."""
        host = HostInfo(
            host_type=LLMHost.OLLAMA,
            name="Ollama",
            default_port=11434,
            api_path="/v1/chat/completions",
            description="Test",
            port=9999,
        )
        
        assert host.endpoint == "http://localhost:9999/v1/chat/completions"
    
    def test_host_info_display_name_detected(self):
        """Test HostInfo display_name when detected."""
        host = HostInfo(
            host_type=LLMHost.OLLAMA,
            name="Ollama",
            default_port=11434,
            api_path="/v1/chat/completions",
            description="Test",
            detected=True,
        )
        
        assert "[detected]" in host.display_name
        assert "Ollama" in host.display_name
    
    def test_host_info_display_name_not_detected(self):
        """Test HostInfo display_name when not detected."""
        host = HostInfo(
            host_type=LLMHost.OLLAMA,
            name="Ollama",
            default_port=11434,
            api_path="/v1/chat/completions",
            description="Test",
            detected=False,
        )
        
        assert "[not found]" in host.display_name


class TestDefaultHosts:
    """Test DEFAULT_HOSTS configuration."""
    
    def test_default_hosts_count(self):
        """Test that DEFAULT_HOSTS has 3 entries."""
        assert len(DEFAULT_HOSTS) == 3
    
    def test_default_hosts_types(self):
        """Test that DEFAULT_HOSTS has correct types."""
        host_types = [h.host_type for h in DEFAULT_HOSTS]
        assert LLMHost.LM_STUDIO in host_types
        assert LLMHost.OLLAMA in host_types
        assert LLMHost.LEMONADE in host_types


class TestIsPortOpen:
    """Test is_port_open function."""
    
    def test_is_port_open_closed(self):
        """Test is_port_open with closed port."""
        # Use a port that's likely closed
        result = is_port_open("localhost", 59999, timeout=0.1)
        assert result is False
    
    @patch("socket.create_connection")
    def test_is_port_open_success(self, mock_create_connection):
        """Test is_port_open with open port."""
        mock_create_connection.return_value = MagicMock()
        
        result = is_port_open("localhost", 8000)
        
        assert result is True
        mock_create_connection.assert_called_once()
    
    @patch("socket.create_connection")
    def test_is_port_open_timeout(self, mock_create_connection):
        """Test is_port_open with timeout."""
        mock_create_connection.side_effect = socket.timeout()
        
        result = is_port_open("localhost", 8000)
        
        assert result is False
    
    @patch("socket.create_connection")
    def test_is_port_open_connection_refused(self, mock_create_connection):
        """Test is_port_open with connection refused."""
        mock_create_connection.side_effect = ConnectionRefusedError()
        
        result = is_port_open("localhost", 8000)
        
        assert result is False


class TestCheckAPIs:
    """Test API checking functions."""
    
    @patch("httpx.get")
    def test_check_lm_studio_api_success(self, mock_get):
        """Test check_lm_studio_api success."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = check_lm_studio_api(8000)
        
        assert result is True
        mock_get.assert_called_once()
    
    @patch("httpx.get")
    def test_check_lm_studio_api_failure(self, mock_get):
        """Test check_lm_studio_api failure."""
        mock_get.side_effect = Exception("Connection failed")
        
        result = check_lm_studio_api(8000)
        
        assert result is False
    
    @patch("httpx.get")
    def test_check_ollama_api_success(self, mock_get):
        """Test check_ollama_api success."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = check_ollama_api(11434)
        
        assert result is True
    
    @patch("httpx.get")
    def test_check_ollama_api_failure(self, mock_get):
        """Test check_ollama_api failure."""
        mock_get.side_effect = Exception("Connection failed")
        
        result = check_ollama_api(11434)
        
        assert result is False
    
    @patch("httpx.get")
    def test_check_lemonade_api_success(self, mock_get):
        """Test check_lemonade_api success."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = check_lemonade_api(8000)
        
        assert result is True
    
    @patch("httpx.get")
    def test_check_lemonade_api_failure(self, mock_get):
        """Test check_lemonade_api failure."""
        mock_get.side_effect = Exception("Connection failed")
        
        result = check_lemonade_api(8000)
        
        assert result is False


class TestDetectLLMHosts:
    """Test detect_llm_hosts function."""
    
    @patch("setup.detector.is_port_open", return_value=False)
    def test_detect_llm_hosts_none_detected(self, mock_port):
        """Test detect_llm_hosts when no hosts are detected."""
        hosts = detect_llm_hosts()
        
        assert len(hosts) == 3
        assert all(not h.detected for h in hosts)
    
    @patch("setup.detector.check_lm_studio_api", return_value=True)
    @patch("setup.detector.is_port_open", return_value=True)
    def test_detect_llm_hosts_lm_studio_detected(self, mock_port, mock_api):
        """Test detect_llm_hosts when LM Studio is detected."""
        hosts = detect_llm_hosts()
        
        lm_studio = next(h for h in hosts if h.host_type == LLMHost.LM_STUDIO)
        assert lm_studio.detected is True
    
    def test_detect_llm_hosts_custom_ports(self):
        """Test detect_llm_hosts with custom ports."""
        custom_ports = {LLMHost.OLLAMA: 9999}
        
        with patch("setup.detector.is_port_open", return_value=False):
            hosts = detect_llm_hosts(custom_ports=custom_ports)
        
        ollama = next(h for h in hosts if h.host_type == LLMHost.OLLAMA)
        assert ollama.port == 9999


class TestGetRecommendedHost:
    """Test get_recommended_host function."""
    
    def test_get_recommended_host_none_detected(self):
        """Test get_recommended_host when no hosts detected."""
        hosts = [
            HostInfo(
                host_type=LLMHost.LM_STUDIO,
                name="LM Studio",
                default_port=8000,
                api_path="/v1/chat/completions",
                description="Test",
                detected=False,
            ),
        ]
        
        result = get_recommended_host(hosts)
        
        assert result is None
    
    def test_get_recommended_host_lm_studio_priority(self):
        """Test that LM Studio has priority."""
        hosts = [
            HostInfo(
                host_type=LLMHost.LM_STUDIO,
                name="LM Studio",
                default_port=8000,
                api_path="/v1/chat/completions",
                description="Test",
                detected=True,
            ),
            HostInfo(
                host_type=LLMHost.OLLAMA,
                name="Ollama",
                default_port=11434,
                api_path="/v1/chat/completions",
                description="Test",
                detected=True,
            ),
        ]
        
        result = get_recommended_host(hosts)
        
        assert result.host_type == LLMHost.LM_STUDIO
    
    def test_get_recommended_host_lemonade_priority(self):
        """Test that Lemonade has priority over Ollama."""
        hosts = [
            HostInfo(
                host_type=LLMHost.OLLAMA,
                name="Ollama",
                default_port=11434,
                api_path="/v1/chat/completions",
                description="Test",
                detected=True,
            ),
            HostInfo(
                host_type=LLMHost.LEMONADE,
                name="Lemonade",
                default_port=8000,
                api_path="/v1/chat/completions",
                description="Test",
                detected=True,
            ),
        ]
        
        result = get_recommended_host(hosts)
        
        assert result.host_type == LLMHost.LEMONADE


class TestValidateEndpoint:
    """Test validate_endpoint function."""
    
    def test_validate_endpoint_valid(self):
        """Test validate_endpoint with valid endpoint."""
        is_valid, error = validate_endpoint("http://localhost:8000/v1/chat/completions")
        
        assert is_valid is True
        assert error is None
    
    def test_validate_endpoint_https(self):
        """Test validate_endpoint with HTTPS."""
        is_valid, error = validate_endpoint("https://localhost:8000/v1/chat/completions")
        
        assert is_valid is True
    
    def test_validate_endpoint_with_ip(self):
        """Test validate_endpoint with IP address."""
        is_valid, error = validate_endpoint("http://192.168.1.100:8000/v1/chat/completions")
        
        assert is_valid is True
    
    def test_validate_endpoint_invalid_format(self):
        """Test validate_endpoint with invalid format."""
        is_valid, error = validate_endpoint("not-a-url")
        
        assert is_valid is False
        assert "Invalid URL format" in error
    
    def test_validate_endpoint_wrong_path(self):
        """Test validate_endpoint with wrong path."""
        is_valid, error = validate_endpoint("http://localhost:8000/wrong/path")
        
        assert is_valid is False
        assert "v1/chat/completions" in error
    
    def test_validate_endpoint_missing_protocol(self):
        """Test validate_endpoint without protocol."""
        is_valid, error = validate_endpoint("localhost:8000/v1/chat/completions")
        
        assert is_valid is False
