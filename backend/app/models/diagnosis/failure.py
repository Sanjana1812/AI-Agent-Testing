"""Rich failure model for Sprint 4 root cause analysis."""

from __future__ import annotations

from typing import TypedDict


class RichFailure(TypedDict, total=False):
    # Existing API fields (backward compatible)
    type: str
    message: str
    severity: str
    expected_element: str | None
    selector: str | None
    available_context: dict | None
    # Extended fields
    step_id: str | None
    action: str | None
    target: str | None
    expected: str | None
    actual: str | None
    exception_type: str | None
    current_url: str | None
    page_title: str | None
    planner_source: str | None
    screenshot_path: str | None
    assertion_results: list[dict]
    website_context_summary: dict | None
    timestamp: str | None
