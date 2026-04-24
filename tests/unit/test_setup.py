"""
Unit tests for setup module.

Tests cover:
- IronSiloConfig initialization and methods
- Configurator class functionality
- Configuration validation
- Environment file generation
"""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from setup.configurator import Configurator, IronSiloConfig, generate_docker_compose_env
from setup.detector import HostInfo, LLMHost


class TestIronSiloConfig:
    """Test IronSiloConfig class."""
    
    def test_config_initialization(self):
        """Test config initialization with defaults."""
        config = IronSiloConfig()
        
        assert config.llm_endpoint == "http://host.docker.internal:8000/v1/chat/completions"
        assert config.llm_port == 8000
        assert config.enable_ironclaw is True
        assert config.enable_searxng is True
        assert config.memory_limit_mb == 4096
        assert config.cpu_limit == 4.0
        assert config.postgres_password == "silo_password"
        assert config.postgres_db == "ironsilo_vault"
        assert config.postgres_user == "silo_admin"
        assert config.custom_settings == {}
    
    def test_to_env_dict(self):
        """Test converting config to environment dict."""
        config = IronSiloConfig()
        config.custom_settings = {"CUSTOM_VAR": "custom_value"}
        
        env_dict = config.to_env_dict()
        
        assert env_dict["LLM_ENDPOINT"] == config.llm_endpoint
        assert env_dict["POSTGRES_DB"] == config.postgres_db
        assert env_dict["POSTGRES_USER"] == config.postgres_user
        assert env_dict["POSTGRES_PASSWORD"] == config.postgres_password
        assert env_dict["ENABLE_IRONCLAW"] == "true"
        assert env_dict["ENABLE_SEARXNG"] == "true"
        assert env_dict["MEMORY_LIMIT_MB"] == "4096"
        assert env_dict["CPU_LIMIT"] == "4.0"
        assert env_dict["CUSTOM_VAR"] == "custom_value"
    
    def test_to_env_string(self):
        """Test converting config to .env file content."""
        config = IronSiloConfig()
        
        env_string = config.to_env_string()
        
        assert "LLM_ENDPOINT=" in env_string
        assert "POSTGRES_DB=" in env_string
        assert "POSTGRES_USER=" in env_string
        assert "POSTGRES_PASSWORD=" in env_string
        assert "ENABLE_IRONCLAW=" in env_string
        assert "ENABLE_SEARXNG=" in env_string
        assert "MEMORY_LIMIT_MB=" in env_string
        assert "CPU_LIMIT=" in env_string
        assert "# IronSilo Configuration" in env_string
    
    def test_to_env_string_with_custom_settings(self):
        """Test .env string with custom settings."""
        config = IronSiloConfig()
        config.custom_settings = {"MY_CUSTOMSetting": "my_value"}
        
        env_string = config.to_env_string()
        
        assert "# Custom Settings" in env_string
        assert "MY_CUSTOMSetting=my_value" in env_string


class TestConfigurator:
    """Test Configurator class."""
    
    def test_configurator_initialization(self):
        """Test configurator initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configurator = Configurator(Path(tmpdir))
            
            assert configurator.workspace_dir == Path(tmpdir)
            assert configurator.env_file == Path(tmpdir) / ".env"
            assert configurator.backup_dir == Path(tmpdir) / "config_backups"
    
    def test_backup_existing_env_no_file(self):
        """Test backup when no .env file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configurator = Configurator(Path(tmpdir))
            
            result = configurator.backup_existing_env()
            
            assert result is None
    
    def test_backup_existing_env_with_file(self):
        """Test backup when .env file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            env_file = tmpdir_path / ".env"
            env_file.write_text("TEST=value")
            
            configurator = Configurator(tmpdir_path)
            
            result = configurator.backup_existing_env()
            
            assert result is not None
            assert result.exists()
            assert result.parent == tmpdir_path / "config_backups"
            assert result.read_text() == "TEST=value"
    
    def test_write_env_file(self):
        """Test writing .env file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configurator = Configurator(Path(tmpdir))
            config = IronSiloConfig()
            
            result = configurator.write_env_file(config)
            
            assert result.exists()
            content = result.read_text()
            assert "LLM_ENDPOINT=" in content
    
    def test_read_existing_config_no_file(self):
        """Test reading config when no file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configurator = Configurator(Path(tmpdir))
            
            result = configurator.read_existing_config()
            
            assert result is None
    
    def test_read_existing_config_with_file(self):
        """Test reading config from existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            env_file = tmpdir_path / ".env"
            env_file.write_text("""
LLM_ENDPOINT=http://localhost:8000/v1/chat/completions
POSTGRES_DB=test_db
POSTGRES_USER=test_user
POSTGRES_PASSWORD=test_password123
ENABLE_IRONCLAW=true
ENABLE_SEARXNG=false
MEMORY_LIMIT_MB=2048
CPU_LIMIT=2.0
CUSTOM_KEY=custom_value
""")
            
            configurator = Configurator(tmpdir_path)
            
            result = configurator.read_existing_config()
            
            assert result is not None
            assert result.llm_endpoint == "http://localhost:8000/v1/chat/completions"
            assert result.postgres_db == "test_db"
            assert result.postgres_user == "test_user"
            assert result.postgres_password == "test_password123"
            assert result.enable_ironclaw is True
            assert result.enable_searxng is False
            assert result.memory_limit_mb == 2048
            assert result.cpu_limit == 2.0
            assert result.custom_settings["CUSTOM_KEY"] == "custom_value"
    
    def test_read_existing_config_invalid_file(self):
        """Test reading config from invalid file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            env_file = tmpdir_path / ".env"
            env_file.write_text("invalid content without equals")
            
            configurator = Configurator(tmpdir_path)
            
            result = configurator.read_existing_config()
            
            # Should return a config object (with defaults) even for invalid file
            # since the invalid line is just skipped
            assert result is not None
    
    def test_validate_config_valid(self):
        """Test validating valid config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configurator = Configurator(Path(tmpdir))
            config = IronSiloConfig()
            config.postgres_password = "longpassword123"
            
            errors = configurator.validate_config(config)
            
            assert len(errors) == 0
    
    def test_validate_config_invalid_endpoint(self):
        """Test validating config with invalid endpoint."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configurator = Configurator(Path(tmpdir))
            config = IronSiloConfig()
            config.llm_endpoint = "invalid-url"
            
            errors = configurator.validate_config(config)
            
            assert any("LLM_ENDPOINT" in error for error in errors)
    
    def test_validate_config_weak_password(self):
        """Test validating config with weak password."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configurator = Configurator(Path(tmpdir))
            config = IronSiloConfig()
            config.postgres_password = "short"
            
            errors = configurator.validate_config(config)
            
            assert any("POSTGRES_PASSWORD" in error for error in errors)
    
    def test_validate_config_low_memory(self):
        """Test validating config with low memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configurator = Configurator(Path(tmpdir))
            config = IronSiloConfig()
            config.memory_limit_mb = 256
            
            errors = configurator.validate_config(config)
            
            assert any("MEMORY_LIMIT_MB" in error for error in errors)
    
    def test_validate_config_low_cpu(self):
        """Test validating config with low CPU."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configurator = Configurator(Path(tmpdir))
            config = IronSiloConfig()
            config.cpu_limit = 0.1
            
            errors = configurator.validate_config(config)
            
            assert any("CPU_LIMIT" in error for error in errors)
    
    def test_create_config_from_host(self):
        """Test creating config from host info."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configurator = Configurator(Path(tmpdir))
            
            host_info = HostInfo(
                host_type=LLMHost.OLLAMA,
                name="Ollama",
                default_port=11434,
                api_path="/v1/chat/completions",
                description="Ollama LLM host",
                port=11434,
            )
            
            config = configurator.create_config_from_host(host_info)
            
            assert config.llm_host == LLMHost.OLLAMA
            assert config.llm_port == 11434


class TestGenerateDockerComposeEnv:
    """Test generate_docker_compose_env function."""
    
    def test_generate_docker_compose_env(self):
        """Test generating docker-compose env file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IronSiloConfig()
            output_path = Path(tmpdir) / "docker.env"
            
            result = generate_docker_compose_env(config, output_path)
            
            assert result == output_path
            assert output_path.exists()
            content = output_path.read_text()
            assert "LLM_ENDPOINT=" in content
