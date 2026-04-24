"""
IronSilo TUI CLI Entry Point.

Provides command-line interface for launching the TUI dashboard.
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional


def main() -> None:
    """
    Main entry point for IronSilo TUI.
    
    Usage:
        ironsilo monitor
        ironsilo-dashboard
    """
    parser = argparse.ArgumentParser(
        description="IronSilo Terminal Dashboard",
        prog="ironsilo",
    )
    
    parser.add_argument(
        "command",
        nargs="?",
        default="monitor",
        choices=["monitor", "dashboard"],
        help="Command to execute (default: monitor)",
    )
    
    parser.add_argument(
        "--refresh",
        type=int,
        default=5,
        help="Refresh interval in seconds (default: 5)",
    )
    
    parser.add_argument(
        "--dark",
        action="store_true",
        help="Start in dark mode",
    )
    
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colors",
    )
    
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version and exit",
    )
    
    args = parser.parse_args()
    
    if args.version:
        from . import __version__
        print(f"IronSilo TUI v{__version__}")
        sys.exit(0)
    
    # Launch the TUI
    launch_tui(refresh_interval=args.refresh, dark_mode=args.dark)


def monitor() -> None:
    """
    Launch the IronSilo monitor dashboard.
    
    This is the main entry point called by the `ironsilo monitor` command.
    """
    launch_tui()


def launch_tui(refresh_interval: int = 5, dark_mode: bool = False) -> None:
    """
    Launch the TUI application.
    
    Args:
        refresh_interval: Data refresh interval in seconds
        dark_mode: Start in dark mode
    """
    try:
        from .app import IronSiloTUI
        
        app = IronSiloTUI()
        app._refresh_interval = refresh_interval
        
        if dark_mode:
            app.dark = True
        
        print("Starting IronSilo Dashboard...")
        print("Press 'q' to quit, 'r' to refresh, 'd' to toggle dark mode")
        print("-" * 60)
        
        app.run()
        
    except ImportError as e:
        print(f"Error: Required dependency missing: {e}")
        print("\nInstall dependencies with:")
        print("  pip install textual")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nDashboard closed.")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
