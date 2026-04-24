"""
IronSilo Setup Wizard package.

Provides interactive setup and configuration for IronSilo.
"""

from .wizard import main, SetupWizard
from .detector import LLMHost, detect_llm_hosts

__version__ = "1.0.0"

__all__ = [
    "main",
    "SetupWizard",
    "LLMHost",
    "detect_llm_hosts",
]
