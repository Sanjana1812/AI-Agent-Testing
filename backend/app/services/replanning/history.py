"""Record replanning history for explainability and API summaries."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.replanning.models import PlanModification, ReplanHistory
from app.services.replanning.plan_diff import diff_remaining_plans


def record_replan(
    *,
    original_remaining: list[dict[str, Any]],
    modified_remaining: list[dict[str, Any]],
    modifications: list[PlanModification],
    trigger_observation: dict[str, Any],
    decision: dict[str, Any],
    reason: str,
    confidence: float,
) -> ReplanHistory:
    diff = diff_remaining_plans(original_remaining, modified_remaining)
    return ReplanHistory(
        original_plan=[dict(step) for step in original_remaining],
        modified_plan=[dict(step) for step in modified_remaining],
        modifications=modifications,
        trigger_observation=dict(trigger_observation),
        decision=dict(decision),
        reason=reason,
        confidence=confidence,
        timestamp=datetime.now(timezone.utc).isoformat(),
        affected_remaining_steps=diff.get("affected_remaining_steps", []),
    )


def build_replanning_summary(history_entries: list[ReplanHistory]) -> dict[str, Any] | None:
    if not history_entries:
        return None

    details: list[dict[str, Any]] = []
    for entry in history_entries:
        original = entry.original_plan[0] if entry.original_plan else {}
        replacement = entry.modified_plan[0] if entry.modified_plan else {}
        details.append(
            {
                "step": entry.trigger_observation.get("step_name", ""),
                "decision": entry.decision.get("decision_type", "REPLAN"),
                "original": original.get("label") or original.get("target") or "",
                "replacement": replacement.get("label") or replacement.get("target") or "",
                "reason": entry.reason,
                "confidence": entry.confidence,
                "affected_remaining_steps": entry.affected_remaining_steps,
            }
        )

    return {
        "replans_made": len(history_entries),
        "details": details,
    }
