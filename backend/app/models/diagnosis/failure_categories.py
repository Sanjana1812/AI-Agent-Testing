"""Standardized failure categories (definitions only — no AI yet)."""

from __future__ import annotations

from enum import Enum


class FailureCategory(str, Enum):
    APPLICATION_BUG = "Application Bug"
    PLANNER_ISSUE = "Planner Issue"
    LOCATOR_ISSUE = "Locator Issue"
    ASSERTION_FAILURE = "Assertion Failure"
    TIMING_ISSUE = "Timing Issue"
    RESPONSIVE_LAYOUT = "Responsive Layout"
    NETWORK_ISSUE = "Network Issue"
    AUTHENTICATION_ISSUE = "Authentication Issue"
    ACCESSIBILITY_ISSUE = "Accessibility Issue"
    UNKNOWN = "Unknown"


FAILURE_TYPE_TO_CATEGORY: dict[str, FailureCategory] = {
    "assertion_failure": FailureCategory.ASSERTION_FAILURE,
    "element_not_found": FailureCategory.LOCATOR_ISSUE,
    "timeout": FailureCategory.TIMING_ISSUE,
    "navigation_error": FailureCategory.NETWORK_ISSUE,
    "http_error": FailureCategory.NETWORK_ISSUE,
    "javascript_error": FailureCategory.APPLICATION_BUG,
    "screenshot_failure": FailureCategory.APPLICATION_BUG,
}
