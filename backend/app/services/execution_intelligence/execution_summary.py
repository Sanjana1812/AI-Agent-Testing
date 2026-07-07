"""Build deterministic execution summaries from adaptive execution history."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.execution_intelligence.models import DecisionType


@dataclass
class ExecutionSummary:
    execution_mode: str
    total_steps: int
    completed_steps: int
    failed_steps: int
    skipped_steps: int
    retry_count: int
    recovery_count: int
    replan_count: int
    adaptive_decision_count: int
    adaptive_used: bool
    final_status: str
    execution_reasoning: str
    execution_findings: list[str] = field(default_factory=list)
    execution_recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_mode": self.execution_mode,
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "skipped_steps": self.skipped_steps,
            "retry_count": self.retry_count,
            "recovery_count": self.recovery_count,
            "replan_count": self.replan_count,
            "adaptive_decision_count": self.adaptive_decision_count,
            "adaptive_used": self.adaptive_used,
            "final_status": self.final_status,
            "execution_reasoning": self.execution_reasoning,
            "execution_findings": list(self.execution_findings),
            "execution_recommendations": list(self.execution_recommendations),
        }


def _decision_counts(export: dict[str, Any] | None) -> tuple[int, int, int, int]:
    execution_context = (export or {}).get("execution_context") or {}
    intelligence_log = execution_context.get("execution_intelligence_log") or []

    adaptive = 0
    retries = 0
    recoveries = 0
    replans = 0
    for entry in intelligence_log:
        decision = entry.get("decision") or {}
        decision_type = str(decision.get("decision_type") or "")
        if decision_type in {
            DecisionType.RETRY.value,
            DecisionType.RECOVER.value,
            DecisionType.SKIP.value,
            DecisionType.REPLAN.value,
        }:
            adaptive += 1
        if decision_type == DecisionType.RETRY.value:
            retries += 1
        elif decision_type == DecisionType.RECOVER.value:
            recoveries += 1
        elif decision_type == DecisionType.REPLAN.value:
            replans += 1

    if execution_context.get("replan_count") is not None:
        replans = int(execution_context.get("replan_count") or 0)
    return adaptive, retries, recoveries, replans


def build_execution_summary(
    result: dict[str, Any],
    *,
    execution_export: dict[str, Any] | None = None,
) -> dict[str, Any]:
    summary = result.get("summary") or {}
    total_steps = int(summary.get("total_steps") or len(result.get("ai_plan") or []) or len(result.get("steps") or []))
    completed_steps = int(summary.get("passed_steps") or 0)
    failed_steps = int(summary.get("failed_steps") or 0)

    execution_context = (execution_export or {}).get("execution_context") or {}
    skipped_steps = len(execution_context.get("skipped_steps") or [])
    adaptive_decision_count, retry_count, recovery_count, replan_count = _decision_counts(execution_export)

    adaptive_used = any(
        count > 0 for count in (skipped_steps, retry_count, recovery_count, replan_count, adaptive_decision_count)
    )
    execution_mode = "ADAPTIVE" if adaptive_used else "STANDARD"
    final_status = str(result.get("status") or summary.get("health") or "unknown").upper()
    health = str(summary.get("health") or ("PASS" if final_status in {"SUCCESS", "PASS"} else "FAIL"))

    findings: list[str] = []
    recommendations: list[str] = []
    if retry_count:
        findings.append(f"Retry succeeded {retry_count} time(s).")
        recommendations.append("Review unstable selectors that required retries.")
    if recovery_count:
        findings.append(f"Popup or modal recovery performed {recovery_count} time(s).")
    if skipped_steps:
        findings.append(f"{skipped_steps} planner step(s) skipped during adaptive execution.")
        recommendations.append("Reduce unnecessary planner steps that require skipping.")
    if replan_count:
        findings.append(f"Dynamic replanning executed {replan_count} time(s).")
        recommendations.append("Improve semantic mapping for replanned journeys.")
    if adaptive_used:
        findings.append("Execution completed adaptively.")
    else:
        findings.append("Execution completed without adaptive interventions.")

    if not recommendations:
        recommendations.append("No execution adaptations were required; maintain current stability.")

    reasoning = (
        f"Execution ran in {execution_mode} mode with {completed_steps}/{total_steps} completed step(s), "
        f"{failed_steps} failed, {skipped_steps} skipped, {retry_count} retries, "
        f"{recovery_count} recoveries, and {replan_count} replans."
    )

    return ExecutionSummary(
        execution_mode=execution_mode,
        total_steps=total_steps,
        completed_steps=completed_steps,
        failed_steps=failed_steps,
        skipped_steps=skipped_steps,
        retry_count=retry_count,
        recovery_count=recovery_count,
        replan_count=replan_count,
        adaptive_decision_count=adaptive_decision_count,
        adaptive_used=adaptive_used,
        final_status=final_status,
        execution_reasoning=reasoning,
        execution_findings=findings,
        execution_recommendations=recommendations,
    ).to_dict() | {"health": health}
