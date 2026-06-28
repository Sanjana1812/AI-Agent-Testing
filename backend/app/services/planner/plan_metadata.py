"""Build planner metadata attached to every run."""

from __future__ import annotations

from datetime import datetime, timezone

PLANNER_VERSION = "3.5.0"
CONTEXT_VERSION = "2.0"


def compute_validation_score(*, plan_steps: int, min_steps: int, max_steps: int, rejections: int) -> float:
    """Simple 0–100 score based on plan size and context validation."""
    if plan_steps < min_steps:
        return max(0.0, 40.0 - rejections * 5)
    size_score = min(100.0, (plan_steps / max_steps) * 70.0)
    rejection_penalty = min(30.0, rejections * 10.0)
    return round(max(0.0, size_score + 30.0 - rejection_penalty), 1)


def build_plan_metadata(
    *,
    planner_source: str,
    planning_time_ms: int,
    validation_score: float,
    provider: str | None = None,
) -> dict:
    return {
        "planner_source": planner_source,
        "planner_version": PLANNER_VERSION,
        "context_version": CONTEXT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "validation_score": validation_score,
        "planning_time_ms": planning_time_ms,
        "provider": provider or planner_source,
    }
