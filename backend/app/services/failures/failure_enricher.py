"""Enrich execution failures with Sprint 4-ready metadata without changing the runner."""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.diagnosis.failure_categories import FAILURE_TYPE_TO_CATEGORY
from app.services.failures.failure_messages import humanize_failure_message


def _failed_steps_by_id(steps: list[dict]) -> dict[str, dict]:
    return {step["id"]: step for step in steps if step.get("status") == "failed"}


def _match_step_for_failure(failure: dict, steps: list[dict], ai_plan: list[dict]) -> tuple[str | None, dict | None]:
    failed = _failed_steps_by_id(steps)
    if len(failed) == 1:
        step_id = next(iter(failed))
        return step_id, failed[step_id]

    failure_type = failure.get("type", "")
    if failure_type == "assertion_failure":
        for step in steps:
            if step.get("status") == "failed" and step.get("assertions"):
                return step.get("id"), step

    for step_id, step in failed.items():
        idx = int(step_id) - 1
        if 0 <= idx < len(ai_plan):
            plan_step = ai_plan[idx]
            if failure.get("expected_element") and failure["expected_element"] in str(plan_step.get("label", "")):
                return step_id, step
    if failed:
        step_id = sorted(failed.keys(), key=int)[0]
        return step_id, failed[step_id]
    return None, None


def _plan_step_for_id(step_id: str | None, ai_plan: list[dict]) -> dict | None:
    if not step_id:
        return None
    idx = int(step_id) - 1
    if 0 <= idx < len(ai_plan):
        return ai_plan[idx]
    return None


def enrich_failures(result: dict, website_context_summary: dict | None = None) -> list[dict]:
    """Extend failure dicts with rich metadata while preserving existing fields."""
    steps = result.get("steps", [])
    ai_plan = result.get("ai_plan", [])
    enriched: list[dict] = []

    for failure in result.get("failures", []):
        record = dict(failure)
        step_id, step = _match_step_for_failure(failure, steps, ai_plan)
        plan_step = _plan_step_for_id(step_id, ai_plan)

        record.setdefault("step_id", step_id)
        record.setdefault("action", plan_step.get("action") if plan_step else None)
        record.setdefault("target", plan_step.get("target") if plan_step else None)
        record.setdefault("selector", record.get("selector") or (plan_step.get("selector") if plan_step else None))
        record.setdefault("expected", record.get("expected_element") or (plan_step.get("label") if plan_step else None))
        record.setdefault("actual", None)
        record.setdefault("exception_type", failure.get("type"))
        record.setdefault("current_url", result.get("url"))
        record.setdefault("page_title", result.get("title"))
        record.setdefault("planner_source", result.get("ai_plan_source"))
        record.setdefault("screenshot_path", result.get("screenshot") or None)
        record.setdefault("assertion_results", step.get("assertions", []) if step else [])
        record.setdefault(
            "website_context_summary",
            record.get("available_context") or website_context_summary,
        )
        record.setdefault("timestamp", datetime.now(timezone.utc).isoformat())

        category = FAILURE_TYPE_TO_CATEGORY.get(failure.get("type", ""))
        if category:
            record.setdefault("category", category.value)

        record["user_message"] = humanize_failure_message(record, plan_step)

        enriched.append(record)

    return enriched
