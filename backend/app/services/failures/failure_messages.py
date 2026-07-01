"""Human-readable failure messages for production reporting."""

from __future__ import annotations

import re


def _clean(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def humanize_failure_message(failure: dict, plan_step: dict | None = None) -> str:
    failure_type = failure.get("type", "")
    expected = _clean(failure.get("expected") or failure.get("expected_element") or (plan_step or {}).get("label"))
    target = _clean(failure.get("target") or (plan_step or {}).get("target"))
    page_title = _clean(failure.get("page_title"))
    raw_message = _clean(failure.get("message"))

    if failure_type == "element_not_found":
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
