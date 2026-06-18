#!/usr/bin/env python3
"""
Interactive Setup Wizard for IronSilo

This wizard guides users through initial configuration,
LLM host selection, and security setup.
"""

from pathlib import Path
from typing import Optional, Callable


class SetupWizard:
    """Interactive setup wizard for IronSilo."""

    def __init__(self):
        self.config = {}
        self.config_file = Path.home() / ".config" / "ironsilo" / "config.env"

    def print_header(self):
        print("=" * 50)
        print("  IronSilo Interactive Setup")
        print("=" * 50)
        print()

    def print_step(self, num: int, total: int, title: str):
        print(f"\n[{num}/{total}] {title}")
        print("-" * 40)

    def get_input(
        self,
        prompt: str,
        default: Optional[str] = None,
        validate: Optional[Callable[[str], bool]] = None,
    ) -> str:
        """Get user input with optional default and validation."""
        while True:
            if default:
                user_input = input(f"{prompt} [{default}]: ").strip() or default
            else:
                user_input = input(f"{prompt}: ").strip()

            if validate:
                if validate(user_input):
                    return user_input
                print("Invalid input. Please try again.")
            else:
                return user_input

    def select_llm_host(self) -> str:
        """Step 1: Select LLM host."""
        self.print_step(1, 5, "Select LLM Host")
        print("Which LLM runner are you using?")
        print("  1) LM Studio")
        print("  2) Ollama")
        print("  3) Lemonade (AMD GPU/ROCm)")
        print("  4)LM Studio with local model")

        choice = self.get_input("Select", "2")

        hosts = {
            "1": "http://localhost:1234/v1",
            "2": "http://localhost:11434",
            "3": "http://localhost:11434",
            "4": "http://localhost:1234/v1",
        }

        return hosts.get(choice, hosts["2"])

    def configure_api_key(self) -> str:
        """Step 2: Configure API key."""
        self.print_step(2, 5, "Configure API Security")
        print("Enter API key (or press Enter for local-only mode): ")

        api_key = self.get_input("API Key", "")
        return api_key or "local-sandbox"

    def configure_ports(self) -> dict:
        """Step 3: Configure ports."""
        self.print_step(3, 5, "Configure Ports")

        traefik = self.get_input("Traefik Web UI Port", "8080")
        khoj = self.get_input("Khoj UI Port", "42110")

        return {"traefik": traefik, "khoj": khoj}

    def configure_resources(self) -> dict:
        """Step 4: Configure resource limits."""
        self.print_step(4, 5, "Configure Resource Limits")

        print("Select resource profile:")
        print("  1) Standard (4GB RAM, 1 CPU)")
        print("  2) Performance (6GB RAM, 2 CPU)")
        print("  3) Maximum (8GB RAM, 4 CPU)")

        choice = self.get_input("Profile", "1")

        profiles = {
            "1": {"ram": "4G", "cpus": "1.0"},
            "2": {"ram": "6G", "cpus": "2.0"},
            "3": {"ram": "8G", "cpus": "4.0"},
        }

        return profiles.get(choice, profiles["1"])

    def configure_security(self) -> dict:
        """Step 5: Configure security."""
        self.print_step(5, 5, "Configure Security")

        print("Enable authentication? (recommended for network access)")
        choice = self.get_input("Enable Auth (y/N)", "n")

        if choice.lower() == "y":
            print("Enter master password:")
            password = self.get_input("Password", "")

            print("Enable encryption for stored data?")
            encrypt = self.get_input("Enable Encryption (y/N)", "y")

            return {
                "auth_enabled": True,
                "password": password,
                "encryption": encrypt.lower() == "y",
            }

        return {"auth_enabled": False, "password": "", "encryption": False}

    def save_config(self):
        """Save configuration to file.
        
        Sensitive values (API keys, passwords) are NOT written to disk.
        They should be set via environment variables at runtime.
        """
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

        unsafe_keys = {"api_key", "password"}

        # Check if config has any sensitive data that shouldn't be written
        has_sensitive = any(
            k in unsafe_keys or (isinstance(v, dict) and any(
                sk in unsafe_keys for sk in v
            ))
            for k, v in self.config.items()
        )

        if has_sensitive:
            # Refuse to write sensitive data to config files
            print("WARNING: Configuration contains sensitive API keys or passwords.")
            print("These will NOT be written to disk. Set them via environment variables.")
            print(f"Only non-sensitive config saved to: {self.config_file}")

        with open(self.config_file, "w") as f:
            f.write("# IronSilo Configuration\n")
            f.write("# SENSITIVE VALUES (API keys, passwords) ARE NOT WRITTEN TO DISK.\n")
            f.write("# Set them via environment variables at runtime.\n")
            for key, value in self.config.items():
                if isinstance(value, dict):
                    f.write(f"\n# {key}\n")
                    for k, v in value.items():
                        if k in sensitive_keys:
                            f.write(f"# {k.upper()}=<set via environment variable>\n")
                        else:
                            f.write(f"{k.upper()}={v}\n")
                else:
                    if key in sensitive_keys:
                        f.write(f"# {key.upper()}=<set via environment variable>\n")
                    else:
                        f.write(f"{key.upper()}={value}\n")

        print(f"\nConfiguration saved to: {self.config_file}")

    def run(self, non_interactive: bool = False):
        """Run the wizard."""
        self.print_header()

        if non_interactive:
            self.config = {
                "llm_endpoint": "http://localhost:11434",
                "api_key": "local-sandbox",
                "ports": {"traefik": "8080", "khoj": "42110"},
                "resources": {"ram": "4G", "cpus": "1.0"},
                "security": {"auth_enabled": False, "password": "", "encryption": True},
            }
            print("Running in non-interactive mode with defaults...")
        else:
            self.config = {
                "llm_endpoint": self.select_llm_host(),
                "api_key": self.configure_api_key(),
                "ports": self.configure_ports(),
                "resources": self.configure_resources(),
                "security": self.configure_security(),
            }

        self.save_config()

        print("\n" + "=" * 50)
        print("  Setup Complete!")
        print("=" * 50)
        print("\nNext steps:")
        print("  1. Start your LLM host (Ollama/LM Studio/Lemonade)")
        print("  2. Run ./Start_Workspace.sh")
        print("  3. Open http://localhost:8080 to access IronSilo")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="IronSilo Setup Wizard")
    parser.add_argument("--non-interactive", "-y", action="store_true", help="Run with default configuration")
    args = parser.parse_args()

    wizard = SetupWizard()
    wizard.run(non_interactive=args.non_interactive)


if __name__ == "__main__":
    main()
