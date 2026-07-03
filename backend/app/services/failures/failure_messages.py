"""Human-readable failure messages for production reporting."""

from __future__ import annotations

import re


def _clean(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def _is_navigation_target(failure: dict, plan_step: dict | None) -> bool:
    target = _clean(failure.get("target") or (plan_step or {}).get("target")).lower()
    label = _clean(failure.get("expected") or failure.get("expected_element") or (plan_step or {}).get("label")).lower()
    return target == "navigation" or "navigation bar" in label or "verify navigation" in label


def _misleading_navigation_selector(selector: str | None) -> bool:
    if not selector:
        return False
    lowered = selector.lower()
    return "has-text" in lowered and "navigation" in lowered


def _navigation_qa_report(selector: str | None, *, landmark_likely: bool = False) -> str:
    observed_selector = selector or "navigation landmark selector chain"
    lines = [
        "Assertion Failed",
        "",
        "Expected:",
        "Navigation landmark should exist.",
        "",
        "Observed:",
        f"Semantic selector {observed_selector} did not match any element.",
    ]
    if landmark_likely:
        lines.extend(
            [
                "",
                "Note:",
                "A navigation landmark (<nav> or role=\"navigation\") appears present in page evidence.",
            ]
        )
    lines.extend(
        [
            "",
            "Likely Cause:",
            "Planner generated an incorrect locator instead of using navigation landmarks.",
            "",
            "Impact:",
            "Navigation verification could not be completed.",
            "",
            "Recommendation:",
            'Use role="navigation", <nav>, or accessibility landmarks.',
        ]
    )
    return "\n".join(lines)


def humanize_failure_message(failure: dict, plan_step: dict | None = None) -> str:
    failure_type = failure.get("type", "")
    expected = _clean(failure.get("expected") or failure.get("expected_element") or (plan_step or {}).get("label"))
    target = _clean(failure.get("target") or (plan_step or {}).get("target"))
    page_title = _clean(failure.get("page_title"))
    raw_message = _clean(failure.get("message"))
    selector = _clean(failure.get("selector") or (plan_step or {}).get("selector"))

    if failure_type in {"element_not_found", "timeout", "assertion_failure"} and _is_navigation_target(
        failure, plan_step
    ):
        return _navigation_qa_report(
            selector,
            landmark_likely=_misleading_navigation_selector(selector),
        )

    if failure_type == "element_not_found":
        if _misleading_navigation_selector(selector):
            return _navigation_qa_report(selector, landmark_likely=True)
        if target == "hero" or "hero" in expected.lower():
            destination = expected.replace("Verify Hero Section", "Hero").replace("Verify Hero", "Hero").strip('" ')
            return f"{destination or 'Expected page section'} did not appear after navigation."
        if target in {"link", "button"} or "click" in expected.lower():
            return "Unable to locate the expected navigation element after page load."
        return f"Could not find the expected element on the page{f' ({expected})' if expected else ''}."

    if failure_type == "timeout":
        subject = expected or page_title or "The target page"
        return f"{subject} did not load within timeout."

    if failure_type == "assertion_failure":
        if "visible" in raw_message.lower() or target == "hero":
            expected_part = expected or "Expected content"
            actual = _clean(failure.get("actual")) or "Different content was shown"
            return f"{expected_part} was not visible.\n\nExpected:\n{expected_part}\n\nFound:\n{actual}"
        return raw_message or "An assertion failed during verification."

    if failure_type == "navigation_error":
        return f"Navigation failed before the test could complete{f': {raw_message}' if raw_message else '.'}"

    if failure_type == "javascript_error":
        return f"A page error interrupted execution{f': {raw_message}' if raw_message else '.'}"

    return raw_message or "The test encountered an unexpected issue."
