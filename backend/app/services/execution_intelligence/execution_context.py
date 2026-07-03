"""Build and update execution context for the intelligence layer."""

from __future__ import annotations

from typing import Any

from app.services.execution_intelligence.models import Decision, DecisionType, ExecutionContext, Observation


def build_execution_context(
    *,
    goal: str,
    website_analysis: dict[str, Any] | None = None,
    strategy: dict[str, Any] | None = None,
    planner_metadata: dict[str, Any] | None = None,
    website_context: dict[str, Any] | None = None,
    total_steps: int = 0,
) -> ExecutionContext:
    return ExecutionContext(
        goal=goal,
        website_analysis=website_analysis,
        strategy=strategy,
        planner_metadata=planner_metadata,
        website_context=website_context,
        total_steps=total_steps,
    )


def update_execution_context(
    context: ExecutionContext,
    observation: Observation,
) -> None:
    context.current_step = observation.step_index
    context.observations.append(observation)

    step_record = {
        "step_index": observation.step_index,
        "step_name": observation.step_name,
        "status": observation.status,
        "current_url": observation.current_url,
    }

    if observation.status == "passed":
        context.completed_steps.append(step_record)
    elif observation.status == "failed":
        context.failed_steps.append(step_record)

    if observation.current_url and observation.current_url not in context.visited_pages:
        context.visited_pages.append(observation.current_url)


def record_skip(
    context: ExecutionContext,
    observation: Observation,
    decision: Decision,
) -> None:
    entry = {
        "step_index": observation.step_index,
        "step_name": observation.step_name,
        "skip_reason": decision.reason,
        "original_decision": DecisionType.ABORT.value,
        "override": DecisionType.SKIP.value,
        "confidence": decision.confidence,
    }
    context.skipped_steps.append(entry)
    context.failed_steps = [
        item
        for item in context.failed_steps
        if item.get("step_index") != observation.step_index
    ]


def record_replan(
    context: ExecutionContext,
    history_entry: dict[str, Any],
) -> None:
    context.replan_count += 1
    context.replan_history.append(history_entry)


def append_intelligence_log(
    context: ExecutionContext,
    *,
    observation: Observation,
    decision: Decision,
    validated: bool,
    outcome: str,
) -> None:
    context.execution_intelligence_log.append(
        {
            "step_index": observation.step_index,
            "step_name": observation.step_name,
            "observation": observation.to_dict(),
            "decision": decision.to_dict(),
            "validated": validated,
            "outcome": outcome,
        }
    )
