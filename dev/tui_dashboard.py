#!/usr/bin/env python3
"""
IronSilo Terminal Dashboard (TUI)

A simple terminal-based dashboard for monitoring
IronSilo resources, containers, and health.
"""
import os
import sys
import time
from datetime import datetime
from typing import Optional


def get_docker_status() -> dict:
    """Get Docker container status."""
    import subprocess
    
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}|{{.Status}}|{{.Ports}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        containers = []
        for line in result.stdout.strip().split("\n"):
            if line:
                parts = line.split("|")
                containers.append({
                    "name": parts[0],
                    "status": parts[1] if len(parts) > 1 else "unknown",
                    "ports": parts[2] if len(parts) > 2 else ""
                })
        return {"containers": containers, "total": len(containers)}
    except Exception as e:
        return {"containers": [], "total": 0, "error": str(e)}


def get_llm_status() -> dict:
    """Get LLM endpoint status."""
    import requests
    
    endpoints = [
        ("http://localhost:11434", "Ollama"),
        ("http://localhost:1234", "LM Studio"),
        ("http://localhost:11434", "Lemonade"),
    ]
    
    for url, name in endpoints:
        try:
            resp = requests.get(f"{url}/api/tags", timeout=2)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                return {"available": True, "name": name, "url": url, "models": len(models)}
        except:
            continue
    
    return {"available": False, "name": "None", "url": "", "models": 0}


def get_resource_usage() -> dict:
    """Get system resource usage."""
    import subprocess
    
    try:
        result = subprocess.run(
            ["docker", "stats", "--no-stream", "--format", "{{.MemUsage}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        total_mem = "0B / 0B"
        for line in result.stdout.strip().split("\n"):
            if line:
                total_mem = line
                break
        
        return {"memory": total_mem}
    except:
        return {"memory": "N/A"}


def get_gpu_info() -> dict:
    """Get GPU info if available."""
    import subprocess
    
    try:
        result = subprocess.run(
            ["glxinfo"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        for line in result.stdout.split("\n"):
            if "OpenGL renderer" in line:
                return {"gpu": line.split(":")[-1].strip()}
    except:
        pass
    
    return {"gpu": "Not available"}


def render_dashboard():
    """Render the terminal dashboard."""
    docker_status = get_docker_status()
    llm_status = get_llm_status()
    resources = get_resource_usage()
    gpu_info = get_gpu_info()
    
    print("\033[2J\033[H")  # Clear screen
    print("=" * 60)
    print("  IronSilo Terminal Dashboard".center(60))
    print("=" * 60)
    print(f"  Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(60))
    print("-" * 60)
    
    # Containers
    print("\n📦 Containers")
    print("-" * 40)
    if docker_status.get("containers"):
        for container in docker_status["containers"]:
            status_icon = "✓" if "Up" in container["status"] else "✗"
            print(f"  {status_icon} {container['name']:<25} {container['status']}")
    else:
        print("  No containers running")
    
    # LLM Status
    print("\n🤖 LLM Status")
    print("-" * 40)
    if llm_status["available"]:
        print(f"  ✓ {llm_status['name']} ({llm_status['url']})")
        print(f"    Models loaded: {llm_status['models']}")
    else:
        print("  ✗ No LLM running")
    
    # Resources
    print("\n💾 Resources")
    print("-" * 40)
    print(f"  Container Memory: {resources['memory']}")
    
    # GPU
    print("\n🎮 GPU")
    print("-" * 40)
    print(f"  {gpu_info['gpu']}")
    
    # Quick Actions
    print("\n⚡ Quick Actions")
    print("-" * 40)
    print("  [s] Start Workspace   [S] Stop Workspace")
    print("  [r] Refresh          [q] Quit")
    print("-" * 60)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="IronSilo TUI Dashboard")
    parser.add_argument("--once", "-o", action="store_true",
                       help="Run once and exit")
    args = parser.parse_args()
    
    if args.once:
        render_dashboard()
        return
    
    print("IronSilo Dashboard - Press 'q' to quit")
    print("Press 'r' to refresh")
    print()
    
    while True:
        render_dashboard()
        
        try:
            if os.name == 'nt':
                import msvcrt
                if msvcrt.kbhit():
                    key = msvcrt.getch().decode()
            else:
                import termios
                import tty
                import select
                
                if select.select([sys.stdin], [], [], 0)[0]:
                    key = sys.stdin.read(1)
                else:
                    key = None
            
            if key:
                if key.lower() == 'q':
                    break
                elif key.lower() == 'r':
                    pass  # Will refresh
                elif key.lower() == 's':
                    os.system("./Start_Workspace.sh &")
                elif key.lower() == 'S':
                    os.system("./Stop_Workspace.sh &")
        except KeyboardInterrupt:
            break
        
        time.sleep(1)


if __name__ == "__main__":
    main()