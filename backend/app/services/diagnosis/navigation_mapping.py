"""Detect navigation semantic-mapping failures for diagnosis."""

from __future__ import annotations

import re
from typing import Any


_MISLEADING_NAV_SELECTOR = re.compile(
    r"has-text\s*\(\s*[\"']?\s*(navigation|nav\s*bar|navbar)\s*[\"']?\s*\)",
    re.I,
)


def is_misleading_navigation_selector(selector: str | None) -> bool:
    if not selector:
        return False
    lowered = str(selector).lower()
    if _MISLEADING_NAV_SELECTOR.search(lowered):
        return True
    return lowered.startswith("button") and "navigation" in lowered


def is_navigation_verification_step(
    failure: dict[str, Any],
    evidence_package: dict[str, Any],
) -> bool:
    step_number = int(failure.get("step_number") or 0)
    step_name = str(failure.get("step_name") or "").lower()
    action = failure.get("action")
    action_target = action.get("target") if isinstance(action, dict) else None
    target = str(failure.get("target") or action_target or "").lower()
    if target == "navigation":
        return True
    if "navigation" in step_name or "nav bar" in step_name:
        return True
    for step in evidence_package.get("execution_timeline") or []:
        if str(step.get("id")) != str(step_number):
            continue
        label = str(step.get("step") or "").lower()
        if "navigation" in label or "nav bar" in label:
            return True
    journey = (evidence_package.get("planner_metadata") or {}).get("generated_journey") or []
    if step_number > 0 and step_number <= len(journey):
        journey_label = str(journey[step_number - 1]).lower()
        if "navigation" in journey_label:
            return True
    return False


def navigation_landmark_present(evidence_package: dict[str, Any]) -> bool:
    dom = evidence_package.get("dom_snapshot") or {}
    nodes = dom.get("nodes") or []
    if any(node.get("tag") == "nav" for node in nodes if isinstance(node, dict)):
        return True

    navigation = dom.get("navigation") or []
    if isinstance(navigation, list) and navigation:
        return True

    sections = dom.get("sections") or []
    for section in sections:
        if not isinstance(section, dict):
            continue
        tag = str(section.get("tag") or "").lower()
        role = str(section.get("role") or "").lower()
        if tag == "nav" or role == "navigation":
            return True

    analysis = evidence_package.get("website_analysis") or {}
    if (analysis.get("navigation_links") or 0) > 0:
        return True

    coverage = evidence_package.get("coverage_report") or {}
    for area in coverage.get("areas") or []:
        if str(area.get("area", "")).lower() == "navigation" and area.get("status") == "tested":
            return True

    return False


def build_navigation_mapping_diagnosis(
    failure: dict[str, Any],
    evidence_package: dict[str, Any],
    *,
    goal: str = "",
) -> dict[str, str] | None:
    """Return tailored diagnosis text when navigation was mapped to a text button selector."""
    if not is_navigation_verification_step(failure, evidence_package):
        return None
    selector = str(failure.get("selector_attempted") or failure.get("selector") or "unknown selector")
    if not is_misleading_navigation_selector(selector):
        return None

    landmark_present = navigation_landmark_present(evidence_package)
    step_name = str(failure.get("step_name") or "Verify Navigation Bar")

    root_cause = (
        f"The planner requested verification of the site's navigation ({step_name}), but the "
        f"semantic mapper generated selector {selector}, which does not match real navigation "
        f"structures on most websites."
    )

    if landmark_present:
        reasoning = (
            f"Planner requested verification of the site's navigation. The semantic mapper "
            f"generated selector {selector}. No such element exists on the page. However, "
            f"evidence indicates a navigation landmark (<nav> or role=\"navigation\") is present. "
            f"This points to incorrect locator selection rather than missing site navigation."
        )
        recommendation = (
            "Update the semantic mapper to prefer role=\"navigation\", <nav>, header navigation, "
            "and accessibility landmarks before visible text selectors such as button:has-text(\"Navigation\")."
        )
    else:
        reasoning = (
            f"Planner requested verification of the site's navigation. The semantic mapper "
            f"generated selector {selector}. No matching element was found, and no navigation "
            f"landmark was detected in the captured evidence. The page may lack a semantic "
            f"<nav> region, or context extraction missed it."
        )
        recommendation = (
            "Prefer role=\"navigation\", <nav>, or header navigation landmarks in the planner. "
            "If the site truly lacks navigation landmarks, adjust the journey to verify header "
            "links or primary menu controls instead."
        )

    return {
        "root_cause": root_cause,
        "reasoning": reasoning,
        "recommendation": recommendation,
        "qa_action": (
            "Re-run navigation verification after the planner emits landmark-based selectors "
            f"aligned with goal: {goal or 'verify primary site navigation'}."
        ),
    }
