"""Determine failure severity from business and evidence context."""

from __future__ import annotations

from typing import Any

from app.services.diagnosis.models import FailureType, SeverityLevel


_HIGH_RISK_DOMAINS = frozenset(
    {"e-commerce", "ecommerce", "finance", "healthcare", "saas", "marketplace", "banking"}
)
_CRITICAL_TYPES = frozenset(
    {FailureType.AUTHENTICATION, FailureType.APPLICATION, FailureType.NETWORK}
)
_LOW_TYPES = frozenset({FailureType.TEST_DESIGN, FailureType.AI_PLANNING, FailureType.ENVIRONMENT})


def _website_type(evidence_package: dict[str, Any]) -> str:
    analysis = evidence_package.get("website_analysis") or {}
    return str(
        analysis.get("website_type")
        or (evidence_package.get("planner_metadata") or {}).get("website_type")
        or ""
    ).lower()


def _business_domain(evidence_package: dict[str, Any]) -> str:
    analysis = evidence_package.get("website_analysis") or {}
    return str(analysis.get("business_domain") or "").lower()


def _high_risk_areas(evidence_package: dict[str, Any]) -> list[str]:
    analysis = evidence_package.get("website_analysis") or {}
    areas = analysis.get("high_risk_areas") or []
    strategy = evidence_package.get("testing_strategy") or {}
    if not areas:
        areas = strategy.get("high_risk_areas") or []
    return [str(a).lower() for a in areas]


def _coverage_percent(evidence_package: dict[str, Any]) -> float | None:
    report = evidence_package.get("coverage_report") or {}
    value = report.get("estimated_coverage_percent")
    return float(value) if value is not None else None


def determine_severity(
    failure_type: FailureType,
    evidence_package: dict[str, Any],
    *,
    business_impact_hint: str = "",
) -> SeverityLevel:
    """Score severity using website context, strategy, and failure type."""
    if failure_type in _LOW_TYPES:
        if failure_type == FailureType.ENVIRONMENT:
            return SeverityLevel.HIGH
        return SeverityLevel.LOW

    website_type = _website_type(evidence_package)
    domain = _business_domain(evidence_package)
    high_risk = _high_risk_areas(evidence_package)
    coverage = _coverage_percent(evidence_package)

    score = 0

    if failure_type in _CRITICAL_TYPES:
        score += 3
    elif failure_type in {FailureType.ASSERTION, FailureType.NAVIGATION}:
        score += 2
    elif failure_type in {FailureType.SELECTOR, FailureType.TIMING, FailureType.DATA}:
        score += 1

    if any(k in website_type for k in ("e-commerce", "ecommerce", "saas", "finance")):
        score += 1
    if any(k in domain for k in _HIGH_RISK_DOMAINS):
        score += 1
    if high_risk:
        score += 1

    summary = evidence_package.get("execution_summary") or {}
    if summary.get("failed_steps", 0) > 1:
        score += 1

    if coverage is not None and coverage < 40:
        score += 1

    if "revenue" in business_impact_hint.lower() or "checkout" in business_impact_hint.lower():
        score += 2

    if score >= 5:
        return SeverityLevel.CRITICAL
    if score >= 3:
        return SeverityLevel.HIGH
    if score >= 1:
        return SeverityLevel.MEDIUM
    return SeverityLevel.LOW
