"""
IronSilo Terminal User Interface (TUI) package.

This package provides a terminal-based dashboard for monitoring
IronSilo services, including container health, resource usage,
and log streaming.
"""

from .app import IronSiloTUI
from .cli import main, monitor

__version__ = "1.0.0"

__all__ = [
    "IronSiloTUI",
    "main",
    "monitor",
]
