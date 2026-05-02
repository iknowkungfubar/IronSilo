#!/usr/bin/env python3
"""
OpenCode Health Monitor & Auto-Heal
Monitors MCP servers, Lemonade, and critical services with auto-restart capability
"""

import subprocess
import time
import json
import sys
from typing import Dict, List, Tuple

class HealthMonitor:
    def __init__(self):
        self.lemonade_url = "http://127.0.0.1:13305/api/v1"
        self.mcp_check_interval = 60  # seconds
        self.services = {}

    def check_lemonade(self) -> Tuple[bool, str]:
        """Check if Lemonade server is running"""
        try:
            import requests
            response = requests.get(f"{self.lemonade_url}/models", timeout=5)
            if response.status_code == 200:
                models = response.json().get("data", [])
                return True, f"Running with {len(models)} models"
        except Exception as e:
            return False, str(e)
        return False, "Unknown error"

    def check_mcp_servers(self) -> List[Dict]:
        """Check MCP server status via OpenCode CLI"""
        try:
            result = subprocess.run(
                ["opencode", "mcp", "list", "--json"],
                capture_output=True,
                text=True,
                timeout=30
            )
            # Parse MCP status from output
            # Format: ●  ✓ godot [90mconnected or ●  ✗ turinpai [91mdisconnected
            lines = result.stdout.split('\n')
            servers = []
            for line in lines:
                if '✓' in line or 'connected' in line.lower():
                    name = line.split()[1] if len(line.split()) > 1 else 'unknown'
                    servers.append({"name": name, "status": "connected"})
                elif '✗' in line or 'disconnected' in line.lower() or 'error' in line.lower():
                    name = line.split()[1] if len(line.split()) > 1 else 'unknown'
                    servers.append({"name": name, "status": "disconnected"})
            return servers
        except Exception as e:
            return [{"name": "opencode-cli", "status": "error", "error": str(e)}]

    def check_opencode_models(self) -> Tuple[bool, str]:
        """Check if OpenCode can list models"""
        try:
            result = subprocess.run(
                ["opencode", "models", "list"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                return True, f"{len(lines)} models available"
            return False, "Failed to list models"
        except Exception as e:
            return False, str(e)

    def restart_lemonade(self) -> bool:
        """Restart Lemonade server"""
        try:
            # Kill existing instances
            subprocess.run(["pkill", "-9", "lemond"], capture_output=True)
            time.sleep(2)

            # Start as correct user with proper cache
            env = {
                "HF_HOME": "/run/media/turin/Data/TurinCode-PAI/lemonade-cache/huggingface"
            }
            subprocess.Popen(
                ["sudo", "-u", "turin", "nohup", "/usr/bin/lemond",
                 "/run/media/turin/Data/TurinCode-PAI/lemonade-cache", "> /tmp/lemonade-turin.log 2>&1"],
                env={**env, **subprocess.os.environ},
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            time.sleep(5)

            # Verify restart
            success, msg = self.check_lemonade()
            return success
        except Exception as e:
            return False

    def restart_mcp(self, mcp_name: str) -> bool:
        """Restart a specific MCP server"""
        scripts = {
            "turinpai": "/etc/opencode/tools/gamedev/turinpai_mcp.py",
            "swarm": "/etc/opencode/tools/gamedev/swarm_orchestrator_mcp.py",
        }

        if mcp_name not in scripts:
            return False

        try:
            # Kill existing
            subprocess.run(["pkill", "-f", mcp_name], capture_output=True)
            time.sleep(1)

            # Restart
            subprocess.Popen(
                ["python3", scripts[mcp_name]],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            time.sleep(2)
            return True
        except Exception as e:
            return False

    def diagnose_and_fix(self) -> Dict:
        """Run diagnostics and attempt fixes"""
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "lemonade": {"status": "unknown"},
            "mcp_servers": [],
            "opencode_models": {"status": "unknown"},
            "fixes_attempted": [],
            "fixes_succeeded": []
        }

        # Check Lemonade
        lemonade_ok, lemonade_msg = self.check_lemonade()
        report["lemonade"] = {"healthy": lemonade_ok, "message": lemonade_msg}

        if not lemonade_ok:
            report["fixes_attempted"].append("Lemonade restart")
            if self.restart_lemonade():
                report["fixes_succeeded"].append("Lemonade")
                report["lemonade"]["healthy"] = True
                report["lemonade"]["message"] = "Restarted successfully"

        # Check MCP servers
        mcp_servers = self.check_mcp_servers()
        report["mcp_servers"] = mcp_servers

        for server in mcp_servers:
            if server.get("status") != "connected":
                if server["name"] in ["turinpai", "swarm"]:
                    report["fixes_attempted"].append(f"{server['name']} restart")
                    if self.restart_mcp(server["name"]):
                        report["fixes_succeeded"].append(server["name"])

        # Check OpenCode models
        models_ok, models_msg = self.check_opencode_models()
        report["opencode_models"] = {"healthy": models_ok, "message": models_msg}

        return report

    def continuous_monitor(self, interval: int = 300):
        """Continuously monitor with auto-heal"""
        print("🔄 Starting Health Monitor with Auto-Heal...")
        print(f"   Check interval: {interval}s")
        print("   Auto-fix enabled: YES")
        print()

        while True:
            try:
                report = self.diagnose_and_fix()

                print(f"\n{'='*60}")
                print(f"Health Report - {report['timestamp']}")
                print(f"{'='*60}")

                # Lemonade status
                lm = report["lemonade"]
                lm_icon = "✅" if lm["healthy"] else "❌"
                print(f"{lm_icon} Lemonade: {lm['message']}")

                # MCP status
                mcp_issues = [m for m in report["mcp_servers"] if m.get("status") != "connected"]
                if mcp_issues:
                    print(f"⚠️  MCP Issues: {len(mcp_issues)}")
                    for m in mcp_issues:
                        print(f"   - {m['name']}: {m.get('status', 'unknown')}")
                else:
                    print("✅ All MCP servers connected")

                # Fixes
                if report["fixes_succeeded"]:
                    print(f"🔧 Auto-fixed: {', '.join(report['fixes_succeeded'])}")
                if report["fixes_attempted"]:
                    print(f"⚠️  Attempted fixes: {', '.join(report['fixes_attempted'])}")

                # Wait before next check
                time.sleep(interval)

            except KeyboardInterrupt:
                print("\n\n🛑 Stopping health monitor...")
                break
            except Exception as e:
                print(f"❌ Monitor error: {e}")
                time.sleep(60)


def quick_check() -> Dict:
    """Run a quick health check and return report"""
    monitor = HealthMonitor()
    return monitor.diagnose_and_fix()


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--continuous":
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 300
        HealthMonitor().continuous_monitor(interval)
    else:
        # Single check with auto-fix
        report = quick_check()

        print(f"\n{'='*60}")
        print("Health Check Report")
        print(f"{'='*60}")

        # Lemonade
        lm = report["lemonade"]
        print(f"\n{'✅' if lm['healthy'] else '❌'} Lemonade: {lm['message']}")

        # MCP
        disconnected = [m for m in report["mcp_servers"] if m.get("status") != "connected"]
        if disconnected:
            print(f"\n⚠️  Disconnected MCP servers ({len(disconnected)}):")
            for m in disconnected:
                print(f"   - {m['name']}")
        else:
            print("\n✅ All MCP servers connected")

        # Fixes
        if report["fixes_succeeded"]:
            print(f"\n🔧 Auto-fixed: {', '.join(report['fixes_succeeded'])}")

        # Exit code
        all_healthy = lm['healthy'] and len(disconnected) == 0
        sys.exit(0 if all_healthy else 1)


if __name__ == "__main__":
    main()
