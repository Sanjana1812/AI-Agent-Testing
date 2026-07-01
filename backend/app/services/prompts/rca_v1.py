"""Root Cause Analysis prompt v1 — failure diagnosis (not invoked in Sprint 4.0)."""

from __future__ import annotations

import json

VERSION = "1.0.0"
PURPOSE = "Analyze structured failure evidence and produce a root cause diagnosis."

TEMPLATE = """You are a Senior QA Engineer performing Root Cause Analysis on a failed automated test.

Analyze the evidence package and produce a structured diagnosis.

Failure summary:
{failure_summary}

Evidence package:
{evidence_json}

Instructions:
- Identify the most likely root cause using only the supplied evidence
- Classify the failure into one standard category
- Assign severity and confidence (0.0 to 1.0)
- Reference specific evidence items in your reasoning
- Provide actionable recommendations and an optional suggested fix

Return ONLY JSON with this shape:
{{
  "summary": "One paragraph executive summary",
  "root_cause": "Primary root cause explanation",
  "category": "Locator Issue | Timing Issue | Assertion Failure | ...",
  "severity": "Critical | High | Medium | Low | Informational",
  "confidence": 0.85,
  "evidence": [
    {{"source": "Assertion", "description": "...", "value": "...", "confidence": 1.0}}
  ],
  "recommendations": ["..."],
  "suggested_fix": {{
    "type": "Selector",
    "title": "...",
    "description": "...",
    "priority": "High",
    "example": "..."
  }}
}}
"""


def render(*, failure_summary: str, evidence_package: dict) -> str:
    evidence_json = json.dumps(evidence_package, indent=2, default=str)
    return TEMPLATE.format(
        failure_summary=failure_summary,
        evidence_json=evidence_json,
    )
