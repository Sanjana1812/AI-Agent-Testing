"""Shared types and helpers for the Assertion Engine."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, TypedDict

from playwright.sync_api import Page

logger = logging.getLogger(__name__)

AssertionRunner = Callable[["AssertionContext"], "AssertionResult"]


class AssertionResult(TypedDict):
    type: str
    expected: str
    actual: str
    passed: bool
    reason: str | None
    duration_ms: int


@dataclass
class AssertionContext:
    """Runtime context passed to every assertion after a Playwright action."""

    page: Page
    action: dict[str, Any]
    url: str
    http_status: int | None = None
    action_duration_ms: int = 0
    screenshot_path: Path | None = None


def build_result(
    *,
    assertion_type: str,
    expected: str,
    actual: str,
    passed: bool,
    reason: str | None = None,
    duration_ms: int = 0,
) -> AssertionResult:
    """Create a normalized assertion result object."""
    return AssertionResult(
        type=assertion_type,
        expected=expected,
        actual=actual,
        passed=passed,
        reason=reason,
        duration_ms=duration_ms,
    )


def run_safe(
    assertion_type: str,
    fn: Callable[[], tuple[bool, str, str, str | None]],
) -> AssertionResult:
    """
    Execute an assertion function with timing and exception handling.

    The callback must return (passed, expected, actual, reason).
    """
    start = time.perf_counter()
    try:
        passed, expected, actual, reason = fn()
        duration_ms = int((time.perf_counter() - start) * 1000)
        if not passed and reason is None:
            reason = f"{assertion_type} failed: expected '{expected}', got '{actual}'"
        return build_result(
            assertion_type=assertion_type,
            expected=expected,
            actual=actual,
            passed=passed,
            reason=reason if not passed else None,
            duration_ms=duration_ms,
        )
    except Exception as exc:
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.warning("[AssertionEngine] %s raised: %s", assertion_type, exc)
        return build_result(
            assertion_type=assertion_type,
            expected="",
            actual="",
            passed=False,
            reason=str(exc),
            duration_ms=duration_ms,
        )
