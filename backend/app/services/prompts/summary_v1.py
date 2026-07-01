"""Run summary prompt v1 — high-level execution summary (not invoked in Sprint 4.0)."""

from __future__ import annotations

import json

VERSION = "1.0.0"
PURPOSE = "Summarize a completed test run for stakeholders."

TEMPLATE = """You are a QA reporting assistant.

Summarize this test run for a non-technical stakeholder.

Run status: {status}
Goal: {goal}
URL: {url}
Health: {health}
Steps passed: {passed_steps}/{total_steps}

Failures:
{failures_json}

Planner source: {planner_source}

Return ONLY JSON:
{{
  "summary": "2-3 sentence overview",
  "highlights": ["key point 1", "key point 2"],
  "risk_level": "Low | Medium | High"
}}
"""


def render(
    *,
    status: str,
    goal: str,
    url: str,
    health: str,
    passed_steps: int,
    total_steps: int,
    failures: list[dict],
    planner_source: str,
) -> str:
    failures_json = json.dumps(failures, indent=2, default=str)
    return TEMPLATE.format(
        status=status,
        goal=goal,
        url=url,
        health=health,
        passed_steps=passed_steps,
        total_steps=total_steps,
        failures_json=failures_json,
        planner_source=planner_source,
    )
