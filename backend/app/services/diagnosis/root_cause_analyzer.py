"""Evidence-based root cause analysis."""

from __future__ import annotations

from typing import Any

from app.services.diagnosis.failure_classifier import _primary_failure, _step_label_from_timeline
from app.services.diagnosis.models import FailureType
from app.services.diagnosis.navigation_mapping import build_navigation_mapping_diagnosis
from app.services.diagnosis.prompts import REASONING_TEMPLATES, ROOT_CAUSE_TEMPLATES


def _website_type(evidence_package: dict[str, Any]) -> str:
    analysis = evidence_package.get("website_analysis") or {}
    return (
        analysis.get("website_type")
        or (evidence_package.get("planner_metadata") or {}).get("website_type")
        or "Unknown"
    )


def _business_domain(evidence_package: dict[str, Any]) -> str:
    analysis = evidence_package.get("website_analysis") or {}
    return analysis.get("business_domain") or "general web"


def _strategy_focus(evidence_package: dict[str, Any]) -> str:
    strategy = evidence_package.get("testing_strategy") or {}
    priorities = strategy.get("execution_priority") or strategy.get("testing_priority") or []
    if priorities:
        return ", ".join(str(p) for p in priorities[:3])
    return strategy.get("testing_strategy") or "core user journeys"


def _execution_priority_text(evidence_package: dict[str, Any]) -> str:
    strategy = evidence_package.get("testing_strategy") or {}
    priorities = strategy.get("execution_priority") or strategy.get("testing_priority") or []
    return ", ".join(str(p) for p in priorities) if priorities else "not specified"


def _assertion_summary(failure: dict[str, Any]) -> str:
    results = failure.get("assertion_results") or []
    if not results:
        return "assertion details unavailable"
    parts = []
    for item in results[:3]:
        if isinstance(item, dict):
            parts.append(
                f"{item.get('type', 'assertion')}: expected {item.get('expected')}, "
                f"got {item.get('actual')} ({'pass' if item.get('passed') else 'fail'})"
            )
    return "; ".join(parts) if parts else "assertion failed"


def _coverage_context(evidence_package: dict[str, Any]) -> tuple[str, str]:
    report = evidence_package.get("coverage_report") or {}
    areas = report.get("areas") or []
    if not areas:
        pct = report.get("estimated_coverage_percent")
        if pct is not None:
            return "overall coverage", f"{round(pct)}% estimated"
        return "coverage", "not reported"
    untested = [a for a in areas if a.get("status") == "not_tested"]
    if untested:
        return untested[0].get("area", "area"), "not tested"
    tested = [a for a in areas if a.get("status") == "tested"]
    if tested:
        return tested[0].get("area", "area"), "tested"
    return areas[0].get("area", "area"), areas[0].get("status", "unknown")


def analyze_root_cause(
    evidence_package: dict[str, Any],
    failure_type: FailureType,
    *,
    goal: str = "",
) -> dict[str, Any]:
    """Produce root cause, reasoning, evidence citations, and alternatives."""
    failure = _primary_failure(evidence_package) or {}
    step_number = int(failure.get("step_number") or 0)
    step_name = str(failure.get("step_name") or "unknown step")
    target_label = _step_label_from_timeline(evidence_package, step_number) or step_name
    selector = str(failure.get("selector_attempted") or failure.get("selector") or "unknown selector")
    current_url = str(failure.get("current_url") or evidence_package.get("final_url") or "unknown URL")
    page_title = str(failure.get("page_title") or evidence_package.get("page_title") or "")
    exception = str(failure.get("exception") or failure.get("message") or "no exception recorded")
    alternatives = failure.get("selector_alternatives") or []

    website_type = _website_type(evidence_package)
    coverage_area, coverage_status = _coverage_context(evidence_package)

    nav_mapping = build_navigation_mapping_diagnosis(failure, evidence_package, goal=goal)

    template_key = failure_type.value
    root_template = ROOT_CAUSE_TEMPLATES.get(template_key, ROOT_CAUSE_TEMPLATES["UNKNOWN"])
    root_cause = nav_mapping["root_cause"] if nav_mapping else root_template.format(
        step_number=step_number or "?",
        step_name=step_name,
        target_label=target_label,
        goal=goal or "the stated test goal",
        selector=selector,
        expected=failure.get("expected") or "expected state",
        actual=failure.get("actual") or "observed state",
        current_url=current_url,
        exception=exception[:240],
        website_type=website_type,
    )

    reasoning_template = REASONING_TEMPLATES.get(template_key)
    if nav_mapping:
        reasoning = nav_mapping["reasoning"]
    elif reasoning_template:
        reasoning = reasoning_template.format(
            website_type=website_type,
            strategy_focus=_strategy_focus(evidence_package),
            target_label=target_label,
            execution_priority=_execution_priority_text(evidence_package),
            selector=selector,
            alternative_count=len(alternatives),
            page_title=page_title or "unknown",
            assertion_summary=_assertion_summary(failure),
            coverage_area=coverage_area,
            coverage_status=coverage_status,
            network_error_count=len(failure.get("network_errors") or []),
            console_error_count=len(failure.get("console_errors") or []),
            http_status=evidence_package.get("http_status") or "unknown",
        )
    else:
        reasoning = (
            f"Evidence from step {step_number} ({step_name}) at {current_url} supports "
            f"a {failure_type.value} classification for a {website_type} property "
            f"({ _business_domain(evidence_package) })."
        )

    supporting_evidence: list[dict[str, Any]] = []

    def add_evidence(source: str, description: str, detail: Any = None) -> None:
        entry: dict[str, Any] = {"source": source, "description": description}
        if detail is not None:
            entry["detail"] = detail
        supporting_evidence.append(entry)

    if selector and selector != "unknown selector":
        add_evidence("failure_evidence", f"Selector attempted: {selector}", selector)
    if exception and exception != "no exception recorded":
        add_evidence("failure_evidence", f"Exception: {exception[:200]}", exception[:400])
    if current_url:
        add_evidence("execution_summary", f"URL at failure: {current_url}", current_url)
    if page_title:
        add_evidence("execution_summary", f"Page title: {page_title}", page_title)

    for err in (failure.get("console_errors") or [])[:3]:
        add_evidence("console_logs", f"Console error: {err}", err)
    for err in (failure.get("network_errors") or [])[:3]:
        add_evidence("network_logs", f"Network error: {err}", err)

    planner = evidence_package.get("planner_metadata") or {}
    if planner.get("planner_confidence") is not None:
        add_evidence(
            "planner_metadata",
            f"Planner confidence: {round(float(planner['planner_confidence']) * 100)}%",
            planner.get("planner_confidence"),
        )
    if planner.get("generated_journey"):
        add_evidence(
            "planner_metadata",
            "Generated journey steps recorded",
            planner.get("generated_journey"),
        )

    coverage = evidence_package.get("coverage_report") or {}
    if coverage.get("estimated_coverage_percent") is not None:
        add_evidence(
            "coverage_report",
            f"Estimated coverage: {round(coverage['estimated_coverage_percent'])}%",
            coverage.get("estimated_coverage_percent"),
        )

    alternative_hypotheses: list[str] = []
    if failure_type == FailureType.SELECTOR:
        if nav_mapping:
            alternative_hypotheses.append(
                "Navigation landmarks exist but the planner emitted a literal text-button locator."
            )
        alternative_hypotheses.append(
            "Element exists but is hidden behind a modal, cookie banner, or responsive breakpoint."
        )
        alternative_hypotheses.append(
            "The page content changed since context extraction; selector drift is likely."
        )
    elif failure_type == FailureType.TEST_DESIGN:
        alternative_hypotheses.append(
            "The element was valid but low priority — failure may be acceptable for smoke coverage."
        )
        alternative_hypotheses.append(
            "Timing caused a misleading failure on a non-critical control."
        )
    elif failure_type == FailureType.TIMING:
        alternative_hypotheses.append(
            "Selector is correct but load performance exceeded the wait threshold."
        )
    elif failure_type == FailureType.NETWORK:
        alternative_hypotheses.append(
            "Transient network instability rather than a persistent routing defect."
        )
    elif failure_type == FailureType.APPLICATION:
        alternative_hypotheses.append(
            "Third-party script error unrelated to first-party application code."
        )
    elif failure_type == FailureType.ENVIRONMENT:
        alternative_hypotheses.append(
            "Missing browser binary or CI sandbox restriction rather than application code."
        )

    return {
        "root_cause": root_cause,
        "reasoning": reasoning,
        "supporting_evidence": supporting_evidence,
        "alternative_hypotheses": alternative_hypotheses,
        "navigation_mapping_override": nav_mapping,
    }
