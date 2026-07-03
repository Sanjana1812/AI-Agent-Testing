"""Classify failures from structured evidence only."""

from __future__ import annotations

import re
from typing import Any

from app.services.diagnosis.models import FailureType
from app.services.planner.semantic_filter import is_ignored_label

_KEYBOARD_SHORTCUT_RE = re.compile(
    r"(show\s*/?\s*hide\s+shortcuts?|"
    r"\b(shift|ctrl|control|alt|cmd|command|meta)\s*\+\s*\w+|"
    r"keyboard\s+shortcut|accessibility\s+shortcut)",
    re.I,
)
_AUTH_PATTERNS = re.compile(
    r"\b(login|sign[\s-]?in|sign[\s-]?up|auth|session|unauthorized|forbidden|401|403)\b",
    re.I,
)
_BROWSER_ENV_PATTERNS = re.compile(
    r"(executable doesn'?t exist|playwright.*not found|browser crashed|chromium is not installed)",
    re.I,
)


def _primary_failure(evidence_package: dict[str, Any]) -> dict[str, Any] | None:
    records = evidence_package.get("failure_evidence") or []
    if records:
        first = records[0]
        return first if isinstance(first, dict) else first
    failures = evidence_package.get("execution_summary", {}).get("failed_steps", 0)
    if failures:
        timeline = evidence_package.get("execution_timeline") or []
        for step in timeline:
            if step.get("status") == "failed":
                return {
                    "step_number": int(step.get("id", 0) or 0),
                    "step_name": step.get("step", "unknown"),
                    "failure_type": "unknown",
                    "exception": "",
                }
    return None


def _step_label_from_timeline(evidence_package: dict[str, Any], step_number: int) -> str:
    for step in evidence_package.get("execution_timeline") or []:
        if str(step.get("id")) == str(step_number):
            name = step.get("step", "")
            if ":" in name:
                return name.split(":", 1)[1].strip()
            return name
    planner = evidence_package.get("planner_metadata") or {}
    journey = planner.get("generated_journey") or []
    if step_number > 0 and step_number <= len(journey):
        return journey[step_number - 1]
    return ""


def _is_test_design_interaction(label: str, goal: str, evidence_package: dict[str, Any]) -> bool:
    if not label:
        return False
    if _KEYBOARD_SHORTCUT_RE.search(label):
        return True
    if is_ignored_label(label):
        return True

    goal_tokens = {t for t in re.findall(r"[a-z]{3,}", goal.lower())}
    label_tokens = {t for t in re.findall(r"[a-z]{3,}", label.lower())}
    if goal_tokens and not goal_tokens.intersection(label_tokens):
        strategy = evidence_package.get("testing_strategy") or {}
        priorities = strategy.get("execution_priority") or strategy.get("testing_priority") or []
        priority_text = " ".join(str(p) for p in priorities).lower()
        label_lower = label.lower()
        if priorities and not any(p.lower() in label_lower or label_lower in p.lower() for p in priorities):
            if is_ignored_label(label) or _KEYBOARD_SHORTCUT_RE.search(label):
                return True
            if priority_text and label_lower not in priority_text:
                shortcut_like = any(k in label_lower for k in ("shortcut", "skip to", "search ctrl"))
                if shortcut_like:
                    return True
    return False


def classify_failure(
    evidence_package: dict[str, Any],
    *,
    goal: str = "",
) -> FailureType:
    """Return the primary failure category from evidence."""
    failure = _primary_failure(evidence_package)
    if not failure:
        summary = evidence_package.get("execution_summary") or {}
        if summary.get("failed_steps", 0) == 0 and summary.get("health") == "PASS":
            return FailureType.UNKNOWN
        return FailureType.UNKNOWN

    raw_type = str(
        failure.get("failure_type")
        or failure.get("type")
        or ""
    ).lower()
    exception = str(failure.get("exception") or failure.get("message") or "")
    step_number = int(failure.get("step_number") or 0)
    step_label = _step_label_from_timeline(evidence_package, step_number)
    selector = str(failure.get("selector_attempted") or failure.get("selector") or "")

    if _BROWSER_ENV_PATTERNS.search(exception):
        return FailureType.ENVIRONMENT

    combined = f"{step_label} {selector} {exception}"
    if _AUTH_PATTERNS.search(combined):
        return FailureType.AUTHENTICATION

    if _is_test_design_interaction(step_label, goal, evidence_package):
        return FailureType.TEST_DESIGN

    if raw_type in {"assertion_failure"} or failure.get("assertion_results"):
        return FailureType.ASSERTION
    if raw_type in {"element_not_found"}:
        return FailureType.SELECTOR
    if raw_type in {"timeout"}:
        return FailureType.TIMING
    if raw_type in {"navigation_error", "http_error"}:
        return FailureType.NETWORK
    if raw_type in {"javascript_error"}:
        return FailureType.APPLICATION

    network_errors = failure.get("network_errors") or []
    if network_errors:
        return FailureType.NETWORK

    console_errors = failure.get("console_errors") or []
    if console_errors and raw_type not in {"element_not_found", "timeout"}:
        return FailureType.APPLICATION

    planner = evidence_package.get("planner_metadata") or {}
    if planner.get("planner_source") == "fallback" and raw_type in {"", "unknown"}:
        return FailureType.AI_PLANNING

    if raw_type in {"screenshot_failure"}:
        return FailureType.ENVIRONMENT

    if "navigation" in step_label.lower() or "open_page" in str(failure.get("action") or ""):
        return FailureType.NAVIGATION

    return FailureType.UNKNOWN
