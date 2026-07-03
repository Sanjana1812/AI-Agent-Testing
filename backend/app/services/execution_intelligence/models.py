"""Sprint 5.0+ — Execution Intelligence data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

EXECUTION_INTELLIGENCE_VERSION = "5.2"


class DecisionType(str, Enum):
    CONTINUE = "CONTINUE"
    RETRY = "RETRY"
    RECOVER = "RECOVER"
    REPLAN = "REPLAN"
    SKIP = "SKIP"
    ABORT = "ABORT"


@dataclass
class Observation:
    step_index: int
    step_name: str
    status: str
    current_url: str
    page_title: str
    selector: str | None
    selector_found: bool
    http_status: int
    console_error_count: int
    network_error_count: int
    modal_detected: bool
    execution_time_ms: int
    step_action: str = ""
    error_message: str | None = None
    total_steps: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_index": self.step_index,
            "step_name": self.step_name,
            "status": self.status,
            "current_url": self.current_url,
            "page_title": self.page_title,
            "selector": self.selector,
            "selector_found": self.selector_found,
            "http_status": self.http_status,
            "console_error_count": self.console_error_count,
            "network_error_count": self.network_error_count,
            "modal_detected": self.modal_detected,
            "execution_time_ms": self.execution_time_ms,
            "step_action": self.step_action,
            "error_message": self.error_message,
            "total_steps": self.total_steps,
        }


@dataclass
class Decision:
    decision_type: DecisionType
    reason: str
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "decision_type": self.decision_type.value,
            "reason": self.reason,
            "confidence": round(self.confidence, 3),
        }
        if self.metadata:
            payload["metadata"] = dict(self.metadata)
        return payload


@dataclass
class ExecutionContext:
    goal: str
    website_analysis: dict[str, Any] | None = None
    strategy: dict[str, Any] | None = None
    planner_metadata: dict[str, Any] | None = None
    website_context: dict[str, Any] | None = None
    current_step: int = 0
    total_steps: int = 0
    completed_steps: list[dict[str, Any]] = field(default_factory=list)
    failed_steps: list[dict[str, Any]] = field(default_factory=list)
    skipped_steps: list[dict[str, Any]] = field(default_factory=list)
    visited_pages: list[str] = field(default_factory=list)
    retry_count: dict[str, int] = field(default_factory=dict)
    recovery_attempts: dict[str, int] = field(default_factory=dict)
    replan_count: int = 0
    replan_history: list[dict[str, Any]] = field(default_factory=list)
    observations: list[Observation] = field(default_factory=list)
    execution_intelligence_log: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "website_analysis": self.website_analysis,
            "strategy": self.strategy,
            "planner_metadata": self.planner_metadata,
            "website_context": self.website_context,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "completed_steps": list(self.completed_steps),
            "failed_steps": list(self.failed_steps),
            "skipped_steps": list(self.skipped_steps),
            "visited_pages": list(self.visited_pages),
            "retry_count": dict(self.retry_count),
            "recovery_attempts": dict(self.recovery_attempts),
            "replan_count": self.replan_count,
            "replan_history": list(self.replan_history),
            "observations": [item.to_dict() for item in self.observations],
            "execution_intelligence_log": list(self.execution_intelligence_log),
        }


@dataclass
class DecisionRecord:
    observation: Observation
    decision: Decision
    validated: bool
    validation_message: str = ""
    outcome: str = "continued"

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation": self.observation.to_dict(),
            "decision": self.decision.to_dict(),
            "validated": self.validated,
            "validation_message": self.validation_message,
            "outcome": self.outcome,
        }


@dataclass
class StepDecisionOutcome:
    """Runner-facing result of intelligence evaluation for one step."""

    observation: Observation
    decision: Decision
    validated: bool
    validation_message: str = ""
    outcome: str = "continued"
    rejection_reason: str | None = None

    @property
    def requires_skip(self) -> bool:
        return self.validated and self.decision.decision_type == DecisionType.SKIP

    @property
    def requires_retry(self) -> bool:
        return self.validated and self.decision.decision_type == DecisionType.RETRY

    @property
    def requires_recover(self) -> bool:
        return self.validated and self.decision.decision_type == DecisionType.RECOVER

    @property
    def requires_abort(self) -> bool:
        return self.decision.decision_type == DecisionType.ABORT

    @property
    def requires_replan(self) -> bool:
        return self.validated and self.decision.decision_type == DecisionType.REPLAN


@dataclass
class ExecutionIntelligenceTrace:
    version: str = EXECUTION_INTELLIGENCE_VERSION
    decisions: list[DecisionRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "decisions": [record.to_dict() for record in self.decisions],
            "decision_count": len(self.decisions),
        }
