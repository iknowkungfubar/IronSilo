"""
Configuration Generator for IronSilo Setup.

Generates .env files and configuration for IronSilo deployment.
"""

from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .detector import LLMHost, HostInfo


class IronSiloConfig:
    """IronSilo configuration settings."""
    
    def __init__(self) -> None:
        self.llm_host: Optional[LLMHost] = None
        self.llm_endpoint: str = "http://host.docker.internal:8000/v1/chat/completions"
        self.llm_port: int = 8000
        self.enable_ironclaw: bool = True
        self.enable_searxng: bool = True
        self.memory_limit_mb: int = 4096
        self.cpu_limit: float = 4.0
        self.postgres_password: str = "silo_password"
        self.postgres_db: str = "ironsilo_vault"
        self.postgres_user: str = "silo_admin"
        self.custom_settings: Dict[str, str] = {}
    
    def to_env_dict(self) -> Dict[str, str]:
        """Convert configuration to environment variables dict."""
        env = {
            "LLM_ENDPOINT": self.llm_endpoint,
            "POSTGRES_DB": self.postgres_db,
            "POSTGRES_USER": self.postgres_user,
            "POSTGRES_PASSWORD": self.postgres_password,
            "ENABLE_IRONCLAW": str(self.enable_ironclaw).lower(),
            "ENABLE_SEARXNG": str(self.enable_searxng).lower(),
            "MEMORY_LIMIT_MB": str(self.memory_limit_mb),
            "CPU_LIMIT": str(self.cpu_limit),
        }
        
        # Add custom settings
        env.update(self.custom_settings)
        
        return env
    
    def to_env_string(self) -> str:
        """Convert configuration to .env file content."""
        lines = [
            "# IronSilo Configuration",
            f"# Generated: {datetime.now().isoformat()}",
            "",
            "# LLM Configuration",
            f"LLM_ENDPOINT={self.llm_endpoint}",
            "",
            "# Database Configuration",
            f"POSTGRES_DB={self.postgres_db}",
            f"POSTGRES_USER={self.postgres_user}",
            f"POSTGRES_PASSWORD={self.postgres_password}",
            "",
            "# Feature Flags",
            f"ENABLE_IRONCLAW={str(self.enable_ironclaw).lower()}",
            f"ENABLE_SEARXNG={str(self.enable_searxng).lower()}",
            "",
            "# Resource Limits",
            f"MEMORY_LIMIT_MB={self.memory_limit_mb}",
            f"CPU_LIMIT={self.cpu_limit}",
        ]
        
        # Add custom settings
        if self.custom_settings:
            lines.append("")
            lines.append("# Custom Settings")
            for key, value in self.custom_settings.items():
                lines.append(f"{key}={value}")
        
        return "\n".join(lines) + "\n"


class Configurator:
    """Handles configuration file generation."""
    
    def __init__(self, workspace_dir: Path):
        self.workspace_dir = Path(workspace_dir)
        self.env_file = self.workspace_dir / ".env"
        self.backup_dir = self.workspace_dir / "config_backups"
    
    def backup_existing_env(self) -> Optional[Path]:
        """
        Backup existing .env file if it exists.
        
        Returns:
            Path to backup file or None
        """
        if not self.env_file.exists():
            return None
        
        # Create backup directory
        self.backup_dir.mkdir(exist_ok=True)
        
        # Create backup with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f".env.backup.{timestamp}"
        
        shutil.copy2(self.env_file, backup_path)
        
        return backup_path
    
    def write_env_file(self, config: IronSiloConfig) -> Path:
        """
        Write .env file with configuration.
        
        Args:
            config: Configuration to write
            
        Returns:
            Path to written file
        """
        # Backup existing file
        self.backup_existing_env()
        
        # Write new file
        self.env_file.write_text(config.to_env_string())
        
        return self.env_file
    
    def read_existing_config(self) -> Optional[IronSiloConfig]:
        """
        Read existing .env file if it exists.
        
        Returns:
            IronSiloConfig or None
        """
        if not self.env_file.exists():
            return None
        
        config = IronSiloConfig()
        
        try:
            content = self.env_file.read_text()
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Parse known settings
                    if key == "LLM_ENDPOINT":
                        config.llm_endpoint = value
                    elif key == "POSTGRES_DB":
                        config.postgres_db = value
                    elif key == "POSTGRES_USER":
                        config.postgres_user = value
                    elif key == "POSTGRES_PASSWORD":
                        config.postgres_password = value
                    elif key == "ENABLE_IRONCLAW":
                        config.enable_ironclaw = value.lower() == "true"
                    elif key == "ENABLE_SEARXNG":
                        config.enable_searxng = value.lower() == "true"
                    elif key == "MEMORY_LIMIT_MB":
                        config.memory_limit_mb = int(value)
                    elif key == "CPU_LIMIT":
                        config.cpu_limit = float(value)
                    else:
                        config.custom_settings[key] = value
            
            return config
            
        except Exception:
            return None
    
    def validate_config(self, config: IronSiloConfig) -> List[str]:
        """
        Validate configuration.
        
        Args:
            config: Configuration to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check LLM endpoint format
        if not config.llm_endpoint.startswith(("http://", "https://")):
            errors.append("LLM_ENDPOINT must be a valid HTTP(S) URL")
        
        # Check password strength
        if len(config.postgres_password) < 8:
            errors.append("POSTGRES_PASSWORD should be at least 8 characters")
        
        # Check resource limits
        if config.memory_limit_mb < 512:
            errors.append("MEMORY_LIMIT_MB should be at least 512")
        
        if config.cpu_limit < 0.5:
            errors.append("CPU_LIMIT should be at least 0.5")
        
        return errors
    
    def create_config_from_host(self, host_info: HostInfo) -> IronSiloConfig:
        """
        Create configuration from detected host.
        
        Args:
            host_info: Detected host information
            
        Returns:
            IronSiloConfig
        """
        config = IronSiloConfig()
        config.llm_host = host_info.host_type
        config.llm_endpoint = host_info.endpoint
        config.llm_port = host_info.port or host_info.default_port
        
        return config


def generate_docker_compose_env(config: IronSiloConfig, output_path: Path) -> Path:
    """
    Generate docker-compose environment file.
    
    Args:
        config: Configuration
        output_path: Path to write .env file
        
    Returns:
        Path to written file
    """
    content = config.to_env_string()
    output_path.write_text(content)
    return output_path


if __name__ == "__main__":
    # Example usage
    config = IronSiloConfig()
    config.llm_endpoint = "http://host.docker.internal:8000/v1/chat/completions"
    
    configurator = Configurator(Path.cwd())
    configurator.write_env_file(config)
    
    print(f"Configuration written to: {configurator.env_file}")
