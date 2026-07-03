"""Build optional execution_intelligence API summary from context/trace."""

from __future__ import annotations

from typing import Any

from app.services.execution_intelligence.models import DecisionType, ExecutionContext
from app.services.replanning.history import build_replanning_summary


def build_execution_intelligence_summary(
    context: ExecutionContext | None,
    trace: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if context is None:
        return None

    adaptive_decisions = 0
    steps_retried = 0
    modals_dismissed = 0
    steps_replanned = 0
    skip_details: list[dict[str, Any]] = []
    retry_details: list[dict[str, Any]] = []
    modal_details: list[dict[str, Any]] = []

    for entry in context.execution_intelligence_log:
        decision = entry.get("decision") or {}
        decision_type = decision.get("decision_type")
        if decision_type in {
            DecisionType.SKIP.value,
            DecisionType.RETRY.value,
            DecisionType.RECOVER.value,
            DecisionType.REPLAN.value,
        }:
            adaptive_decisions += 1

        outcome = entry.get("outcome")
        if outcome == "retried":
            steps_retried += 1
        if outcome == "recovered":
            modals_dismissed += 1
        if outcome == "replanned":
            steps_replanned += 1

    for skipped in context.skipped_steps:
        skip_details.append(
            {
                "step": skipped.get("step_name", ""),
                "reason": skipped.get("skip_reason", ""),
                "confidence": skipped.get("confidence", 0.0),
            }
        )

    for entry in context.execution_intelligence_log:
        decision = entry.get("decision") or {}
        if decision.get("decision_type") == DecisionType.RETRY.value:
            metadata = decision.get("metadata") or {}
            retry_details.append(
                {
                    "step": entry.get("step_name", ""),
                    "attempts": metadata.get("retry_number", 1),
                    "outcome": "passed" if entry.get("outcome") == "continued" else "failed",
                }
            )
        if decision.get("decision_type") == DecisionType.RECOVER.value:
            modal_details.append(
                {
                    "step": entry.get("step_name", ""),
                    "dismissed": entry.get("outcome") == "recovered",
                }
            )

    replanning_summary = build_replanning_summary_from_context(context)

    if (
        adaptive_decisions == 0
        and not context.skipped_steps
        and not replanning_summary
    ):
        return None

    payload: dict[str, Any] = {
        "adaptive_decisions_made": adaptive_decisions,
        "steps_skipped": len(context.skipped_steps),
        "steps_retried": steps_retried,
        "modals_dismissed": modals_dismissed,
        "steps_replanned": steps_replanned,
        "skip_details": skip_details,
        "retry_details": retry_details,
        "modal_details": modal_details,
        "version": trace.get("version") if trace else None,
    }
    if replanning_summary:
        payload["replanning_summary"] = replanning_summary
    return payload


def build_replanning_summary_from_context(context: ExecutionContext) -> dict[str, Any] | None:
    if not context.replan_history:
        return None
    from app.services.replanning.models import ReplanHistory

    entries = []
    for item in context.replan_history:
        entries.append(
            ReplanHistory(
                original_plan=item.get("original_plan", []),
                modified_plan=item.get("modified_plan", []),
                modifications=[],
                trigger_observation=item.get("trigger_observation", {}),
                decision=item.get("decision", {}),
                reason=item.get("reason", ""),
                confidence=float(item.get("confidence", 0.0)),
                timestamp=item.get("timestamp", ""),
                affected_remaining_steps=item.get("affected_remaining_steps", []),
            )
        )
    return build_replanning_summary(entries)


def build_summary_from_export(export: dict[str, Any] | None) -> dict[str, Any] | None:
    if not export:
        return None
    context_data = export.get("execution_context")
    if not context_data:
        return None
    context = ExecutionContext(
        goal=context_data.get("goal", ""),
        website_analysis=context_data.get("website_analysis"),
        strategy=context_data.get("strategy"),
        planner_metadata=context_data.get("planner_metadata"),
        website_context=context_data.get("website_context"),
        current_step=int(context_data.get("current_step", 0)),
        total_steps=int(context_data.get("total_steps", 0)),
        completed_steps=list(context_data.get("completed_steps", [])),
        failed_steps=list(context_data.get("failed_steps", [])),
        skipped_steps=list(context_data.get("skipped_steps", [])),
        visited_pages=list(context_data.get("visited_pages", [])),
        retry_count=dict(context_data.get("retry_count", {})),
        recovery_attempts=dict(context_data.get("recovery_attempts", {})),
        replan_count=int(context_data.get("replan_count", 0)),
        replan_history=list(context_data.get("replan_history", [])),
        execution_intelligence_log=list(context_data.get("execution_intelligence_log", [])),
    )
    return build_execution_intelligence_summary(context, export)
