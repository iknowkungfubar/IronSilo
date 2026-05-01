#!/usr/bin/env python3
"""
PAI Algorithm Integration - IronForge Autonomy Layer

Implements the PAI (Personal AI Infrastructure) Algorithm v2.0 for autonomous task completion.

Phase 2: Autonomy
- OBSERVE → PLAN → EXECUTE → VERIFY loop
- Ideal State Criteria (ISC) extraction
- Five Completion Gates verification
- Wisdom frame generation
"""
import json
import os
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class TaskState(Enum):
    """Task lifecycle states."""
    OBSERVING = "observe"
    PLANNING = "plan" 
    EXECUTING = "execute"
    VERIFYING = "verify"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class IdealStateCriteria:
    """Ideal State Criteria for a task."""
    criteria: List[str]
    verification_fn: Optional[callable] = None
    
    def is_complete(self, result: Dict[str, Any]) -> bool:
        """Check if ISC is satisfied."""
        if self.verification_fn:
            return self.verification_fn(result)
        return all(c in result.get("state", "") for c in self.criteria)


@dataclass
class CompletionGate:
    """Five Completion Gates."""
    gate_id: int
    name: str
    description: str
    passed: bool = False
    
    @classmethod
    def default_gates(cls) -> List['CompletionGate']:
        """Generate standard completion gates."""
        return [
            cls(1, "Build Gate", "Code compiles without errors"),
            cls(2, "Test Gate", "All tests pass"),
            cls(3, "Integration Gate", "Components integrate correctly"),
            cls(4, "Security Gate", "SecurityScan Passes, No CVEs"),
            cls(5, "Performance Gate", "Meets latency/resource requirements"),
        ]


@dataclass
class WisdomFrame:
    """Wisdom frame for learning from execution."""
    task: str
    approach: str
    outcome: str
    lessons: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "approach": self.approach,
            "outcome": self.outcome,
            "lessons": self.lessons,
            "timestamp": self.timestamp
        }


class PAIAlgorithm:
    """PAI Algorithm orchestrator for autonomous execution."""
    
    def __init__(self, task: str, isc: Optional[List[str]] = None):
        self.task = task
        self.state = TaskState.OBSERVING
        self.isc = IdealStateCriteria(isc or [])
        self.gates = CompletionGate.default_gates()
        self.wisdom_frames: List[WisdomFrame] = []
        self.iteration = 0
        self.max_iterations = 10
        
    def observe(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """OBSERVE phase: Gather context and extract ISC."""
        self.state = TaskState.OBSERVING
        return {
            "phase": "observe",
            "context": context,
            "timestamp": time.time(),
            "notes": self._analyze_context(context)
        }
    
    def _analyze_context(self, context: Dict[str, Any]) -> List[str]:
        """Analyze context and generate observations."""
        observations = []
        if "error" in context:
            observations.append(f"Error detected: {context['error']}")
        if "files" in context:
            observations.append(f"Found {len(context['files'])} relevant files")
        if "tests" in context:
            observations.append(f"{len(context.get('tests', []))} existing tests")
        return observations
    
    def plan(self, observations: List[str]) -> List[str]:
        """PLAN phase: Generate task plan from observations."""
        self.state = TaskState.PLANNING
        plan = []
        for i, obs in enumerate(observations, 1):
            plan.append(f"Step {i}: {obs}")
        plan.append(f"Step {len(observations)+1}: Verify with completion gates")
        return plan
    
    def execute(self, plan: List[str]) -> Dict[str, Any]:
        """EXECUTE phase: Run the plan."""
        self.state = TaskState.EXECUTING
        self.iteration += 1
        return {
            "phase": "execute",
            "plan": plan,
            "iteration": self.iteration,
            "status": "running"
        }
    
    def verify(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """VERIFY phase: Check completion gates."""
        self.state = TaskState.VERIFYING
        gate_results = []
        
        for gate in self.gates:
            # Simple heuristics for gate passing
            if gate.gate_id == 1 and "build" in result:
                gate.passed = result.get("build", {}).get("success", False)
            elif gate.gate_id == 2 and "tests" in result:
                gate.passed = result.get("tests", {}).get("passed", False)
            elif gate.gate_id == 3:
                gate.passed = result.get("integration", {}).get("success", True)
            elif gate.gate_id == 4:
                gate.passed = "vulnerabilities" not in result or result.get("vulnerabilities", []) == []
            else:
                gate.passed = True  # Default pass for perf gate
                
            gate_results.append({
                "gate": gate.name,
                "passed": gate.passed
            })
        
        all_passed = all(g["passed"] for g in gate_results)
        self.state = TaskState.COMPLETED if all_passed else TaskState.EXECUTING
        
        return {
            "phase": "verify",
            "gates": gate_results,
            "all_passed": all_passed,
            "can_continue": self.iteration < self.max_iterations
        }
    
    def record_wisdom(self, approach: str, outcome: str, lessons: List[str]) -> None:
        """Record a wisdom frame."""
        frame = WisdomFrame(
            task=self.task,
            approach=approach,
            outcome=outcome,
            lessons=lessons
        )
        self.wisdom_frames.append(frame)
    
    def get_wisdom(self) -> List[Dict[str, Any]]:
        """Get all recorded wisdom frames."""
        return [f.to_dict() for f in self.wisdom_frames]
    
    def run_autonomous(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Run full autonomous loop."""
        # Observe
        obs_result = self.observe(context)
        observations = obs_result.get("notes", [])
        
        # Plan  
        plan = self.plan(observations)
        
        # Execute (would integrate with actual code execution)
        exec_result = self.execute(plan)
        
        # Verify
        verify_result = self.verify(exec_result)
        
        return {
            "task": self.task,
            "state": self.state.value,
            "iteration": self.iteration,
            "observations": observations,
            "plan": plan,
            "gates": verify_result.get("gates", []),
            "wisdom": self.get_wisdom()
        }


def create_pai_algorithm(task: str, isc: Optional[List[str]] = None) -> PAIAlgorithm:
    """Factory function to create PAI Algorithm instance."""
    return PAIAlgorithm(task, isc)


if __name__ == "__main__":
    # Demo execution
    pai = create_pai_algorithm(
        task="Fix MCP servers",
        isc=["All servers respond", "No connection errors"]
    )
    result = pai.run_autonomous({
        "context": "Testing MCP server integration",
        "error": None
    })
    print(json.dumps(result, indent=2))