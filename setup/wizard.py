"""
Interactive Setup Wizard for IronSilo.

Provides a guided setup experience for configuring IronSilo.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .detector import LLMHost, HostInfo, detect_llm_hosts, get_recommended_host, validate_endpoint
from .configurator import Configurator, IronSiloConfig


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def print_section(text: str) -> None:
    """Print a section header."""
    print(f"\n--- {text} ---\n")


def print_success(text: str) -> None:
    """Print success message."""
    print(f"✓ {text}")


def print_error(text: str) -> None:
    """Print error message."""
    print(f"✗ {text}")


def print_warning(text: str) -> None:
    """Print warning message."""
    print(f"⚠ {text}")


def get_input(prompt: str, default: Optional[str] = None) -> str:
    """Get user input with optional default."""
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "
    
    try:
        response = input(prompt).strip()
        return response if response else (default or "")
    except EOFError:
        return default or ""


def get_yes_no(prompt: str, default: bool = True) -> bool:
    """Get yes/no input from user."""
    default_str = "Y/n" if default else "y/N"
    response = get_input(f"{prompt} ({default_str})", "y" if default else "n")
    return response.lower() in ("y", "yes", "")


def select_option(prompt: str, options: List[str], default: int = 0) -> int:
    """Let user select from numbered options."""
    print(prompt)
    for i, option in enumerate(options, 1):
        marker = "→" if i - 1 == default else " "
        print(f"  {marker} {i}. {option}")
    
    while True:
        try:
            response = get_input("\nSelect option", str(default + 1))
            choice = int(response) - 1
            if 0 <= choice < len(options):
                return choice
            print_error("Invalid option")
        except ValueError:
            print_error("Please enter a number")


class SetupWizard:
    """Interactive setup wizard for IronSilo."""
    
    def __init__(self, workspace_dir: Optional[Path] = None):
        self.workspace_dir = workspace_dir or Path.cwd()
        self.config = IronSiloConfig()
        self.detected_hosts: List[HostInfo] = []
    
    def run(self) -> IronSiloConfig:
        """
        Run the setup wizard.
        
        Returns:
            IronSiloConfig with user's choices
        """
        print_header("IronSilo Setup Wizard")
        print("Welcome to the IronSilo interactive setup wizard!")
        print("This will guide you through configuring your local AI development sandbox.\n")
        
        try:
            # Step 1: Detect LLM hosts
            self._step_detect_hosts()
            
            # Step 2: Select LLM host
            self._step_select_host()
            
            # Step 3: Configure features
            self._step_configure_features()
            
            # Step 4: Configure resources
            self._step_configure_resources()
            
            # Step 5: Configure security
            self._step_configure_security()
            
            # Step 6: Review and save
            self._step_review_and_save()
            
            return self.config
            
        except KeyboardInterrupt:
            print("\n\nSetup cancelled.")
            sys.exit(1)
    
    def _step_detect_hosts(self) -> None:
        """Step 1: Detect installed LLM hosts."""
        print_section("Step 1: Detecting LLM Hosts")
        print("Scanning for installed LLM hosts...\n")
        
        self.detected_hosts = detect_llm_hosts()
        
        for host in self.detected_hosts:
            if host.detected:
                print_success(f"{host.name} detected on port {host.port}")
            else:
                print(f"  {host.name} not detected")
        
        detected = [h for h in self.detected_hosts if h.detected]
        if not detected:
            print_warning("\nNo LLM hosts detected!")
            print("You'll need to configure the endpoint manually.")
            print("Please install one of: LM Studio, Ollama, or Lemonade")
    
    def _step_select_host(self) -> None:
        """Step 2: Select LLM host."""
        print_section("Step 2: Select LLM Host")
        
        detected = [h for h in self.detected_hosts if h.detected]
        
        if detected:
            # Show detected hosts
            options = [h.display_name for h in detected]
            options.append("Custom endpoint")
            
            recommended = get_recommended_host(self.detected_hosts)
            default_idx = 0
            if recommended:
                for i, h in enumerate(detected):
                    if h.host_type == recommended.host_type:
                        default_idx = i
                        break
            
            choice = select_option(
                "Select your LLM host:",
                options,
                default=default_idx,
            )
            
            if choice < len(detected):
                selected = detected[choice]
                self.config.llm_host = selected.host_type
                self.config.llm_endpoint = selected.endpoint
                self.config.llm_port = selected.port or selected.default_port
                print_success(f"Selected: {selected.name}")
                return
        
        # Custom endpoint
        print("\nConfigure custom LLM endpoint:")
        
        while True:
            endpoint = get_input(
                "LLM endpoint URL",
                "http://localhost:8000/v1/chat/completions"
            )
            
            is_valid, error = validate_endpoint(endpoint)
            if is_valid:
                self.config.llm_endpoint = endpoint
                self.config.llm_host = LLMHost.CUSTOM
                print_success(f"Endpoint configured: {endpoint}")
                break
            else:
                print_error(f"Invalid endpoint: {error}")
    
    def _step_configure_features(self) -> None:
        """Step 3: Configure optional features."""
        print_section("Step 3: Configure Features")
        
        # IronClaw agent
        self.config.enable_ironclaw = get_yes_no(
            "Enable IronClaw autonomous agent?",
            default=True
        )
        print_success(f"IronClaw: {'enabled' if self.config.enable_ironclaw else 'disabled'}")
        
        # SearxNG private search
        self.config.enable_searxng = get_yes_no(
            "Enable SearxNG private web search?",
            default=True
        )
        print_success(f"SearxNG: {'enabled' if self.config.enable_searxng else 'disabled'}")
    
    def _step_configure_resources(self) -> None:
        """Step 4: Configure resource limits."""
        print_section("Step 4: Resource Limits")
        print("IronSilo runs in Docker with resource limits to protect your system.\n")
        
        # Memory limit
        memory_input = get_input(
            "Memory limit for containers (MB)",
            str(self.config.memory_limit_mb)
        )
        try:
            self.config.memory_limit_mb = int(memory_input)
        except ValueError:
            print_warning("Invalid number, using default")
        
        # CPU limit
        cpu_input = get_input(
            "CPU limit (cores)",
            str(self.config.cpu_limit)
        )
        try:
            self.config.cpu_limit = float(cpu_input)
        except ValueError:
            print_warning("Invalid number, using default")
        
        print_success(f"Memory limit: {self.config.memory_limit_mb}MB")
        print_success(f"CPU limit: {self.config.cpu_limit} cores")
    
    def _step_configure_security(self) -> None:
        """Step 5: Configure security settings."""
        print_section("Step 5: Security Configuration")
        
        # Postgres password
        print("Database credentials for PostgreSQL:")
        
        self.config.postgres_user = get_input(
            "Database user",
            self.config.postgres_user
        )
        
        self.config.postgres_password = get_input(
            "Database password (min 8 chars)",
            self.config.postgres_password
        )
        
        if len(self.config.postgres_password) < 8:
            print_warning("Password is short, consider using a longer one")
        
        print_success("Security configured")
    
    def _step_review_and_save(self) -> None:
        """Step 6: Review and save configuration."""
        print_section("Step 6: Review & Save")
        
        print("Configuration summary:")
        print(f"  LLM Endpoint: {self.config.llm_endpoint}")
        print(f"  IronClaw: {'enabled' if self.config.enable_ironclaw else 'disabled'}")
        print(f"  SearxNG: {'enabled' if self.config.enable_searxng else 'disabled'}")
        print(f"  Memory Limit: {self.config.memory_limit_mb}MB")
        print(f"  CPU Limit: {self.config.cpu_limit} cores")
        print(f"  Database: {self.config.postgres_db}")
        print(f"  DB User: {self.config.postgres_user}")
        
        if not get_yes_no("\nSave this configuration?", default=True):
            print_warning("Configuration not saved")
            return
        
        # Create configurator and save
        configurator = Configurator(self.workspace_dir)
        
        # Validate
        errors = configurator.validate_config(self.config)
        if errors:
            print_error("Configuration errors:")
            for error in errors:
                print(f"  - {error}")
            return
        
        # Save
        env_path = configurator.write_env_file(self.config)
        print_success(f"Configuration saved to: {env_path}")
        
        print("\nYou can now start IronSilo with:")
        if sys.platform == "win32":
            print("  .\\Start_Workspace.bat")
        else:
            print("  ./Start_Workspace.sh")


def main() -> None:
    """Main entry point for setup wizard."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="IronSilo Setup Wizard",
        prog="ironsilo-setup",
    )
    
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path.cwd(),
        help="Workspace directory (default: current directory)",
    )
    
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run in non-interactive mode (use defaults)",
    )
    
    args = parser.parse_args()
    
    if args.non_interactive:
        # Use defaults
        config = IronSiloConfig()
        configurator = Configurator(args.workspace)
        env_path = configurator.write_env_file(config)
        print(f"Default configuration written to: {env_path}")
    else:
        # Run interactive wizard
        wizard = SetupWizard(args.workspace)
        wizard.run()


if __name__ == "__main__":
    main()
