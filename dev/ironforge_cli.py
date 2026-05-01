#!/usr/bin/env python3
"""
IronForge CLI - Unified Entry Point

Usage: ironforge <command> [options]

Commands:
    status          - Show IronForge status
    run <task>    - Run a coding task
    loop          - Start autonomous loop
    wisdom        - Show wisdom frames
    resources     - Show resource status
"""
import argparse
import json
import sys
from pathlib import Path

# Add dev/ to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from ironforge_integration import ForgeGodIntegration, get_integration
from pai_algorithm import create_pai_algorithm
from wisdom_frames import create_wisdom_frame, CompletionGates, ExecutionResult
from resource_manager import ResourceManager, get_resource_manager


def cmd_status(args):
    """Show IronForge status."""
    integration = get_integration()
    data = integration.status()
    data["resources"] = get_resource_manager().get_status()
    print(json.dumps(data, indent=2))
    return 0


def cmd_run(args):
    """Run a coding task."""
    integration = get_integration()
    result = integration.run_task(args.task, args.model)
    print(json.dumps(result, indent=2))
    return 0 if result.get("success") else 1


def cmd_loop(args):
    """Start autonomous loop."""
    integration = get_integration()
    result = integration.start_loop(args.prd, args.workers)
    print(json.dumps(result, indent=2))
    return 0 if result.get("success") else 1


def cmd_wisdom(args):
    """Show wisdom frames."""
    pai = create_pai_algorithm(args.task)
    wisdom = pai.get_wisdom()
    print(json.dumps(wisdom, indent=2))
    return 0


def cmd_resources(args):
    """Show resource status."""
    rm = get_resource_manager()
    print(json.dumps(rm.get_status(), indent=2))
    return 0


def main():
    parser = argparse.ArgumentParser(description="IronForge CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # status
    subparsers.add_parser("status", help="Show IronForge status")
    
    # run
    run_parser = subparsers.add_parser("run", help="Run a coding task")
    run_parser.add_argument("task", help="Task description")
    run_parser.add_argument("--model", default="ollama:qwen3-coder-next", help="Model to use")
    
    # loop
    loop_parser = subparsers.add_parser("loop", help="Start autonomous loop")
    loop_parser.add_argument("--prd", default=".forgegod/prd.json", help="PRD path")
    loop_parser.add_argument("--workers", type=int, default=1, help="Worker count")
    
    # wisdom
    wisdom_parser = subparsers.add_parser("wisdom", help="Show wisdom frames")
    wisdom_parser.add_argument("--task", default="default", help="Task name")
    
    # resources
    subparsers.add_parser("resources", help="Show resource status")
    
    args = parser.parse_args()
    
    commands = {
        "status": cmd_status,
        "run": cmd_run,
        "loop": cmd_loop,
        "wisdom": cmd_wisdom,
        "resources": cmd_resources,
    }
    
    return commands.get(args.command, lambda _: 1)(args)


if __name__ == "__main__":
    sys.exit(main())