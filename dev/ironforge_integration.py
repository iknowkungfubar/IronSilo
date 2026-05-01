#!/usr/bin/env python3
"""
IronForge Integration - ForgeGod ↔ OpenCode/PAI Wiring

This module provides the integration between ForgeGod coding harness
and OpenCode/PAI orchestration layer.

Phase 1: Foundation
- ForgeGod callable from OpenCode as skill/tool
- SochDB as ForgeGod memory backend
- Lemonade as primary ForgeGod backend (AMD ROCm)
"""
import json
import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

# Configuration paths
FORGEGOD_CONFIG = os.path.expanduser("~/.forgegod/config.toml")
LEMONADE_HOST = os.environ.get("LEMONADE_HOST", "http://localhost:11434")
TURINPAI_CONFIG = os.path.expanduser("~/.config/turinpai/config.json")


class ForgeGodIntegration:
    """ForgeGod integration with OpenCode/PAI."""
    
    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = workspace_root or os.getcwd()
        self.forgegod_available = self._check_forgegod()
        self.lemonade_available = self._check_lemonade()
        self.sochdb_available = self._check_sochdb()
    
    def _check_forgegod(self) -> bool:
        """Check if ForgeGod is installed."""
        try:
            result = subprocess.run(
                ["forgegod", "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def _check_lemonade(self) -> bool:
        """Check if Lemonade is running."""
        try:
            import requests
            resp = requests.get(f"{LEMONADE_HOST}/api/tags", timeout=2)
            return resp.status_code == 200
        except:
            return False
    
    def _check_sochdb(self) -> bool:
        """Check if SochDB is available."""
        try:
            import sochdb
            return True
        except ImportError:
            return False
    
    def status(self) -> Dict[str, Any]:
        """Get integration status."""
        return {
            "forgegod": self.forgegod_available,
            "lemonade": self.lemonade_available,
            "sochdb": self.sochdb_available,
            "workspace": self.workspace_root,
            "ready": self.forgegod_available and self.lemonade_available
        }
    
    def run_task(self, task: str, model: str = "ollama:qwen3-coder-next") -> Dict[str, Any]:
        """Run a coding task via ForgeGod."""
        if not self.forgegod_available:
            return {"error": "ForgeGod not installed"}
        
        # Use Lemonade model if available
        if self.lemonade_available and "ollama" in model:
            model = f"ollama:{model.split(':')[1] if ':' in model else 'qwen3-coder-next'}"
        
        try:
            result = subprocess.run(
                ["forgegod", "run", f"--model={model}", task],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=self.workspace_root
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }
        except subprocess.TimeoutExpired:
            return {"error": "Task timeout"}
        except Exception as e:
            return {"error": str(e)}
    
    def start_loop(self, prd_path: str = ".forgegod/prd.json", workers: int = 1) -> Dict[str, Any]:
        """Start ForgeGod autonomous loop."""
        if not self.forgegod_available:
            return {"error": "ForgeGod not installed"}
        
        prd_full = os.path.join(self.workspace_root, prd_path)
        if not os.path.exists(prd_full):
            return {"error": f"PRD not found: {prd_path}"}
        
        try:
            proc = subprocess.Popen(
                ["forgegod", "loop", f"--prd={prd_full}", f"--workers={workers}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.workspace_root
            )
            return {
                "success": True,
                "pid": proc.pid,
                "message": f"Loop started with PID {proc.pid}"
            }
        except Exception as e:
            return {"error": str(e)}
    
    def stop_loop(self) -> Dict[str, Any]:
        """Stop ForgeGod autonomous loop."""
        try:
            subprocess.run(["pkill", "-f", "forgegod loop"], timeout=5)
            return {"success": True, "message": "Loop stopped"}
        except Exception as e:
            return {"error": str(e)}


def get_integration() -> ForgeGodIntegration:
    """Get ForgeGod integration instance."""
    return ForgeGodIntegration()


if __name__ == "__main__":
    integration = get_integration()
    print(json.dumps(integration.status(), indent=2))
