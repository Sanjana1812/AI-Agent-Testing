"""Structured evidence package for Root Cause Analysis (Sprint 4.0)."""

from __future__ import annotations

from typing import TypedDict

from app.models.diagnosis.evidence import Evidence


class EvidencePackage(TypedDict, total=False):
    """Single structured evidence bundle collected when a test execution fails."""

    screenshot_path: str | None
    dom_snapshot: dict | str | None
    current_url: str | None
    page_title: str | None
    current_action: str | None
    current_step: dict | None
    selector: str | None
    website_context: dict | None
    planner_metadata: dict | None
    assertion_results: list[dict]
    console_errors: list[str]
    network_errors: list[str]
    timestamp: str
    evidence_items: list[Evidence]
    failure: dict
