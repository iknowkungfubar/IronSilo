"""
LLM Host Detection for IronSilo Setup.

Detects installed LLM hosts (LM Studio, Ollama, Lemonade) and their configurations.
"""

from __future__ import annotations

import socket
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class LLMHost(str, Enum):
    """Supported LLM hosts."""
    
    LM_STUDIO = "lmstudio"
    OLLAMA = "ollama"
    LEMONADE = "lemonade"
    CUSTOM = "custom"


@dataclass
class HostInfo:
    """Information about an LLM host."""
    
    host_type: LLMHost
    name: str
    default_port: int
    api_path: str
    description: str
    detected: bool = False
    port: Optional[int] = None
    version: Optional[str] = None
    
    @property
    def endpoint(self) -> str:
        """Get the full API endpoint."""
        port = self.port or self.default_port
        return f"http://localhost:{port}{self.api_path}"
    
    @property
    def display_name(self) -> str:
        """Get display name with detection status."""
        status = "[detected]" if self.detected else "[not found]"
        return f"{self.name} (port {self.default_port}) {status}"


# Default host configurations
DEFAULT_HOSTS = [
    HostInfo(
        host_type=LLMHost.LM_STUDIO,
        name="LM Studio",
        default_port=8000,
        api_path="/v1/chat/completions",
        description="Easy-to-use desktop app for running local LLMs",
    ),
    HostInfo(
        host_type=LLMHost.OLLAMA,
        name="Ollama",
        default_port=11434,
        api_path="/v1/chat/completions",
        description="Command-line tool for running local LLMs",
    ),
    HostInfo(
        host_type=LLMHost.LEMONADE,
        name="Lemonade",
        default_port=8000,
        api_path="/v1/chat/completions",
        description="Optimized for AMD GPUs on Linux",
    ),
]


def is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """
    Check if a port is open on a host.
    
    Args:
        host: Hostname or IP address
        port: Port number
        timeout: Connection timeout in seconds
        
    Returns:
        True if port is open, False otherwise
    """
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def check_lm_studio_api(port: int = 8000) -> bool:
    """
    Check if LM Studio API is available.
    
    Args:
        port: LM Studio port
        
    Returns:
        True if API is responding
    """
    import httpx
    
    try:
        response = httpx.get(
            f"http://localhost:{port}/v1/models",
            timeout=2.0,
        )
        return response.status_code == 200
    except Exception:
        return False


def check_ollama_api(port: int = 11434) -> bool:
    """
    Check if Ollama API is available.
    
    Args:
        port: Ollama port
        
    Returns:
        True if API is responding
    """
    import httpx
    
    try:
        response = httpx.get(
            f"http://localhost:{port}/api/tags",
            timeout=2.0,
        )
        return response.status_code == 200
    except Exception:
        return False


def check_lemonade_api(port: int = 8000) -> bool:
    """
    Check if Lemonade API is available.
    
    Args:
        port: Lemonade port
        
    Returns:
        True if API is responding
    """
    import httpx
    
    try:
        response = httpx.get(
            f"http://localhost:{port}/v1/models",
            timeout=2.0,
        )
        return response.status_code == 200
    except Exception:
        return False


def detect_llm_hosts(custom_ports: Optional[Dict[LLMHost, int]] = None) -> List[HostInfo]:
    """
    Detect installed LLM hosts.
    
    Args:
        custom_ports: Optional dict of custom ports to check
        
    Returns:
        List of HostInfo with detection results
    """
    results = []
    custom_ports = custom_ports or {}
    
    for host_info in DEFAULT_HOSTS:
        # Check custom port if provided
        port = custom_ports.get(host_info.host_type, host_info.default_port)
        host_info.port = port
        
        # Check if port is open
        if not is_port_open("localhost", port):
            results.append(host_info)
            continue
        
        # Check specific API based on host type
        if host_info.host_type == LLMHost.LM_STUDIO:
            host_info.detected = check_lm_studio_api(port)
        elif host_info.host_type == LLMHost.OLLAMA:
            host_info.detected = check_ollama_api(port)
        elif host_info.host_type == LLMHost.LEMONADE:
            host_info.detected = check_lemonade_api(port)
        
        results.append(host_info)
    
    return results


def get_recommended_host(hosts: List[HostInfo]) -> Optional[HostInfo]:
    """
    Get recommended LLM host from detected hosts.
    
    Priority: LM Studio > Lemonade > Ollama > Custom
    
    Args:
        hosts: List of detected hosts
        
    Returns:
        Recommended host or None
    """
    # Filter to detected hosts
    detected = [h for h in hosts if h.detected]
    
    if not detected:
        return None
    
    # Priority order
    priority = [LLMHost.LM_STUDIO, LLMHost.LEMONADE, LLMHost.OLLAMA]
    
    for host_type in priority:
        for host in detected:
            if host.host_type == host_type:
                return host
    
    return detected[0]


def validate_endpoint(endpoint: str) -> Tuple[bool, Optional[str]]:
    """
    Validate an LLM endpoint URL.
    
    Args:
        endpoint: Endpoint URL to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    import re
    
    # Basic URL validation
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    if not url_pattern.match(endpoint):
        return False, "Invalid URL format"
    
    # Check if it's a chat completions endpoint
    if not endpoint.endswith("/v1/chat/completions"):
        return False, "Endpoint should end with /v1/chat/completions"
    
    return True, None


if __name__ == "__main__":
    # Run detection
    print("Detecting LLM hosts...")
    hosts = detect_llm_hosts()
    
    for host in hosts:
        status = "✓" if host.detected else "✗"
        print(f"  {status} {host.display_name}")
    
    recommended = get_recommended_host(hosts)
    if recommended:
        print(f"\nRecommended: {recommended.name}")
        print(f"Endpoint: {recommended.endpoint}")
    else:
        print("\nNo LLM hosts detected. Please install LM Studio, Ollama, or Lemonade.")
