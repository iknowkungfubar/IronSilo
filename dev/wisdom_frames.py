#!/usr/bin/env python3
"""
Wisdom Frame System - IronForge Intelligence Layer

Phase 3: Intelligence
- Wisdom frame extraction from execution
- Completion gate validators
- Learning from execution patterns
"""
import json
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class GateType(Enum):
    """Completion gate types."""
    BUILD = "build"
    TEST = "test"
    INTEGRATION = "integration"
    SECURITY = "security"
    PERFORMANCE = "performance"


@dataclass
class GateResult:
    """Result of a completion gate check."""
    gate_type: GateType
    passed: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0


@dataclass 
class WisdomFrame:
    """Wisdom frame capturing execution learning."""
    task_id: str
    approach: str
    execution_time_ms: float
    success: bool
    gates_passed: List[str]
    gates_failed: List[str]
    lessons: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "approach": self.approach,
            "execution_time_ms": self.execution_time_ms,
            "success": self.success,
            "gates_passed": self.gates_passed,
            "gates_failed": self.gates_failed,
            "lessons": self.lessons,
            "timestamp": self.timestamp
        }


@dataclass
class ExecutionResult:
    """Container for execution results."""
    success: bool
    output: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    duration_ms: float = 0.0
    artifacts: Dict[str, Any] = field(default_factory=dict)


class CompletionGates:
    """Five Completion Gates validator."""
    
    @staticmethod
    def check_build(result: ExecutionResult) -> GateResult:
        """Gate 1: Build compiles without errors."""
        passed = result.success and "error" not in result.errors
        return GateResult(
            gate_type=GateType.BUILD,
            passed=passed,
            message="Build gate passed" if passed else "Build failed",
            details={"errors": result.errors}
        )
    
    @staticmethod
    def check_test(result: ExecutionResult) -> GateResult:
        """Gate 2: All tests pass."""
        passed = result.success and "PASSED" in result.output
        return GateResult(
            gate_type=GateType.TEST,
            passed=passed,
            message="Test gate passed" if passed else "Tests failed",
            details={"output": result.output[:500]}
        )
    
    @staticmethod
    def check_integration(artifacts: Dict[str, Any]) -> GateResult:
        """Gate 3: Components integrate correctly."""
        has_integrations = "integrations" in artifacts
        passed = has_integrations and artifacts.get("integrations", True)
        return GateResult(
            gate_type=GateType.INTEGRATION,
            passed=passed,
            message="Integration gate passed" if passed else "Integration issues",
            details=artifacts
        )
    
    @staticmethod
    def check_security(scan_result: Dict[str, Any]) -> GateResult:
        """Gate 4: Security scan passes, no CVEs."""
        vuln_count = len(scan_result.get("vulnerabilities", []))
        passed = vuln_count == 0
        return GateResult(
            gate_type=GateType.SECURITY,
            passed=passed,
            message="Security gate passed" if passed else f"Found {vuln_count} vulnerabilities",
            details={"vulnerabilities": scan_result.get("vulnerabilities", [])}
        )
    
    @staticmethod
    def check_performance(metrics: Dict[str, Any]) -> GateResult:
        """Gate 5: Meets latency/resource requirements."""
        latency = metrics.get("latency_ms", float("inf"))
        memory_mb = metrics.get("memory_mb", float("inf"))
        passed = latency < 1000 and memory_mb < 4096
        return GateResult(
            gate_type=GateType.PERFORMANCE,
            passed=passed,
            message="Performance gate passed" if passed else "Performance issues",
            details={"latency_ms": latency, "memory_mb": memory_mb}
        )
    
    @classmethod
    def validate_all(cls, result: ExecutionResult, 
                    artifacts: Optional[Dict[str, Any]] = None,
                    security: Optional[Dict[str, Any]] = None,
                    metrics: Optional[Dict[str, Any]] = None) -> List[GateResult]:
        """Run all five completion gates."""
        gates = []
        
        gates.append(cls.check_build(result))
        gates.append(cls.check_test(result))
        gates.append(cls.check_integration(artifacts or {}))
        gates.append(cls.check_security(security or {"vulnerabilities": []}))
        gates.append(cls.check_performance(metrics or {"latency_ms": 0, "memory_mb": 0}))
        
        return gates


class WisdomExtractor:
    """Extract wisdom from execution."""
    
    @staticmethod
    def extract(result: ExecutionResult, gates: List[GateResult], task_id: str, approach: str) -> WisdomFrame:
        """Extract wisdom from execution result."""
        passed = [g.gate_type.value for g in gates if g.passed]
        failed = [g.gate_type.value for g in gates if not g.passed]
        
        lessons = []
        if not result.success:
            lessons.append("Execution failed - check errors")
        if failed:
            lessons.append(f"Failed gates: {', '.join(failed)}")
        if "warnings" in result.warnings:
            lessons.append("Review warnings for edge cases")
            
        return WisdomFrame(
            task_id=task_id,
            approach=approach,
            execution_time_ms=result.duration_ms,
            success=result.success,
            gates_passed=passed,
            gates_failed=failed,
            lessons=lessons
        )


def create_wisdom_frame(task_id: str, approach: str, 
                     result: ExecutionResult,
                     artifacts: Optional[Dict[str, Any]] = None,
                     security: Optional[Dict[str, Any]] = None,
                     metrics: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create wisdom frame with full validation."""
    gates = CompletionGates.validate_all(result, artifacts, security, metrics)
    frame = WisdomExtractor.extract(result, gates, task_id, approach)
    return {
        "frame": frame.to_dict(),
        "gates": [{"gate": g.gate_type.value, "passed": g.passed, "message": g.message} for g in gates]
    }


if __name__ == "__main__":
    result = ExecutionResult(
        success=True,
        output="Build successful\nPASSED: all tests",
        errors=[],
        warnings=["Deprecation warning in lib"],
        duration_ms=1250.0
    )
    
    wisdom = create_wisdom_frame(
        task_id="fix_mcp",
        approach="rewrite_jsonrpc",
        result=result,
        security={"vulnerabilities": []},
        metrics={"latency_ms": 50, "memory_mb": 512}
    )
    
    print(json.dumps(wisdom, indent=2))