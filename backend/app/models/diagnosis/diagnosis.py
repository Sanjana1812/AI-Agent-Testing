"""Diagnosis data model (Sprint 4 ready — no AI calls yet)."""

from __future__ import annotations

from typing import TypedDict

from app.models.diagnosis.evidence import Evidence
from app.models.diagnosis.suggested_fix import SuggestedFix


class Diagnosis(TypedDict, total=False):
    summary: str
    root_cause: str
    category: str
    severity: str
    confidence: float
    evidence: list[Evidence]
    recommendations: list[str]
    suggested_fix: SuggestedFix
    provider: str
    latency_ms: int
