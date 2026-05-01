#!/usr/bin/env python3
"""
Resource Manager - IronForge Optimization Layer

Phase 4: Optimization
- VRAM management for AMD RX 7900 GRE
- Model loading orchestration
- Safe concurrent model limits
"""
import json
import os
import subprocess
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class LoadState(Enum):
    """Model load state."""
    AVAILABLE = "available"
    LOADED = "loaded"
    IN_USE = "in_use"


@dataclass
class ModelInfo:
    """Model information."""
    name: str
    size: str
    quant: str
    vram_mb: int
    state: LoadState = LoadState.AVAILABLE


class ResourceManager:
    """Manage GPU/RAM resources for local LLM loading."""
    
    # VRAM limits for AMD RX 7900 GRE (16GB)
    MAX_VRAM_MB = 16384
    SAFE_VRAM_MB = 14000
    
    # Safe model combinations
    SAFE_CONFIGS = [
        {"models": ["8b"], "vram": 4800, "description": "1x 8B (Q4_K_M)"},
        {"models": ["14b"], "vram": 8000, "description": "1x 14B (Q4_K_M)"},
        {"models": ["8b", "8b"], "vram": 9600, "description": "2x 8B (Q4_K_M)"},
    ]
    
    def __init__(self):
        self.vram_used_mb = 0
        self.loaded_models: Dict[str, ModelInfo] = {}
        self._refresh_gpu_info()
    
    def _refresh_gpu_info(self) -> None:
        """Get current GPU info."""
        try:
            result = subprocess.run(
                ["glxinfo"],
                capture_output=True,
                text=True,
                timeout=10
            )
            for line in result.stdout.split("\n"):
                if "OpenGL renderer" in line:
                    self.gpu_name = line.split(":")[-1].strip()
                    break
        except Exception as e:
            self.gpu_name = "Unknown"
    
    def get_status(self) -> Dict[str, Any]:
        """Get resource status."""
        return {
            "gpu": self.gpu_name,
            "vram_total_mb": self.MAX_VRAM_MB,
            "vram_used_mb": self.vram_used_mb,
            "vram_free_mb": self.MAX_VRAM_MB - self.vram_used_mb,
            "loaded_models": [
                {"name": m.name, "size": m.size, "state": m.state.value}
                for m in self.loaded_models.values()
            ]
        }
    
    def can_load(self, model: ModelInfo) -> bool:
        """Check if model can be loaded."""
        return (self.vram_used_mb + model.vram_mb) <= self.SAFE_VRAM_MB
    
    def load_model(self, model: ModelInfo) -> Dict[str, Any]:
        """Load a model."""
        if not self.can_load(model):
            return {
                "success": False,
                "error": "Insufficient VRAM",
                "free_mb": self.MAX_VRAM_MB - self.vram_used_mb,
                "required_mb": model.vram_mb
            }
        
        self.vram_used_mb += model.vram_mb
        model.state = LoadState.LOADED
        self.loaded_models[model.name] = model
        
        return {
            "success": True,
            "vram_used_mb": self.vram_used_mb,
            "model": model.name
        }
    
    def unload_model(self, model_name: str) -> Dict[str, Any]:
        """Unload a model."""
        if model_name not in self.loaded_models:
            return {"success": False, "error": "Model not loaded"}
        
        model = self.loaded_models[model_name]
        self.vram_used_mb -= model.vram_mb
        model.state = LoadState.AVAILABLE
        del self.loaded_models[model_name]
        
        return {
            "success": True,
            "vram_used_mb": self.vram_used_mb
        }
    
    def safe_configs(self) -> List[Dict[str, Any]]:
        """Return safe loading configurations."""
        return self.SAFE_CONFIGS
    
    def find_safe_config(self, model_count: int) -> Optional[Dict[str, Any]]:
        """Find safe config for given model count."""
        for config in self.SAFE_CONFIGS:
            if len(config["models"]) == model_count:
                return config
        return None


def get_resource_manager() -> ResourceManager:
    """Get resource manager instance."""
    return ResourceManager()


if __name__ == "__main__":
    rm = get_resource_manager()
    print(json.dumps(rm.get_status(), indent=2))