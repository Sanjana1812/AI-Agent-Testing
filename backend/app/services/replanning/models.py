"""Sprint 5.2 — Dynamic replanning data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

REPLANNING_VERSION = "5.2"
DEFAULT_CONFIDENCE_THRESHOLD = 0.7
DEFAULT_MAX_REPLANS = 2


@dataclass
class PlanCandidate:
    step_index: int
    original_step: dict[str, Any]
    replacement_step: dict[str, Any]
    confidence: float
    reason: str
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_index": self.step_index,
            "original_step": dict(self.original_step),
            "replacement_step": dict(self.replacement_step),
            "confidence": round(self.confidence, 3),
            "reason": self.reason,
            "source": self.source,
        }

    @property
    def replacement_label(self) -> str:
        return str(self.replacement_step.get("label") or self.replacement_step.get("target") or "")


@dataclass
class PlanModification:
    operation: str
    target_step: int
    replacement: dict[str, Any] | None
    reason: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "target_step": self.target_step,
            "replacement": dict(self.replacement) if self.replacement else None,
            "reason": self.reason,
            "confidence": round(self.confidence, 3),
        }


@dataclass
class ReplanHistory:
    original_plan: list[dict[str, Any]]
    modified_plan: list[dict[str, Any]]
    modifications: list[PlanModification]
    trigger_observation: dict[str, Any]
    decision: dict[str, Any]
    reason: str
    confidence: float
    timestamp: str
    affected_remaining_steps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_plan": [dict(step) for step in self.original_plan],
            "modified_plan": [dict(step) for step in self.modified_plan],
            "modifications": [item.to_dict() for item in self.modifications],
            "trigger_observation": dict(self.trigger_observation),
            "decision": dict(self.decision),
            "reason": self.reason,
            "confidence": round(self.confidence, 3),
            "timestamp": self.timestamp,
            "affected_remaining_steps": list(self.affected_remaining_steps),
        }


@dataclass
class ReplanResult:
    success: bool
    modified_remaining_plan: list[dict[str, Any]]
    history: ReplanHistory | None = None
    rejection_reason: str | None = None
    explainability: dict[str, Any] = field(default_factory=dict)
