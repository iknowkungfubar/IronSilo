#!/usr/bin/env python3
"""
Interactive Setup Wizard for IronSilo

This wizard guides users through initial configuration,
LLM host selection, and security setup.
"""

import os
from pathlib import Path
from typing import Optional, Callable


class SetupWizard:
    """Interactive setup wizard for IronSilo."""

    def __init__(self):
        self.config = {}
        self._api_key = ""     # Never written to disk — use env var IRONSILO_API_KEY
        self._password = ""    # Never written to disk — use env var IRONSILO_PASSWORD
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
        """Step 5: Configure security.

        Password is stored on self._password, NEVER in the returned config dict,
        so save_config() never writes it to disk.
        """
        self.print_step(5, 5, "Configure Security")

        print("Enable authentication? (recommended for network access)")
        choice = self.get_input("Enable Auth (y/N)", "n")

        self._password = ""
        if choice.lower() == "y":
            print("Enter master password:")
            self._password = self.get_input("Password", "")

            print("Enable encryption for stored data?")
            encrypt = self.get_input("Enable Encryption (y/N)", "y")

            return {
                "auth_enabled": True,
                "encryption": encrypt.lower() == "y",
            }

        return {"auth_enabled": False, "encryption": False}

    def save_config(self):
        """Save configuration to disk.

        Only non-sensitive configuration keys are written (no API keys or passwords).
        Those are stored in self._api_key and self._password and NEVER written to disk.
        Set them via IRONSILO_API_KEY and IRONSILO_PASSWORD environment variables at runtime.
        """
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

        # Restrict config file permissions to owner-only
        original_umask = os.umask(0o077)
        try:
            with open(self.config_file, "w") as f:
                f.write("# IronSilo Configuration\n")
                f.write("# API keys and passwords are NOT stored in this file.\n")
                f.write("# Set them via IRONSILO_API_KEY and IRONSILO_PASSWORD env vars.\n")
                f.write("\n")
                for key, value in self.config.items():
                    if isinstance(value, dict):
                        f.write(f"\n# {key}\n")
                        for k, v in value.items():
                            f.write(f"{k.upper()}={v}\n")
                    else:
                        f.write(f"{key.upper()}={value}\n")

        finally:
            os.umask(original_umask)

        print(f"\nConfiguration saved to: {self.config_file}")

    def run(self, non_interactive: bool = False):
        """Run the wizard."""
        self.print_header()

        if non_interactive:
            self.config = {
                "llm_endpoint": "http://localhost:11434",
                "ports": {"traefik": "8080", "khoj": "42110"},
                "resources": {"ram": "4G", "cpus": "1.0"},
                "security": {"auth_enabled": False, "encryption": True},
            }
            self._api_key = "local-sandbox"
            print("Running in non-interactive mode with defaults...")
        else:
            self._api_key = self.configure_api_key()
            self.config = {
                "llm_endpoint": self.select_llm_host(),
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
