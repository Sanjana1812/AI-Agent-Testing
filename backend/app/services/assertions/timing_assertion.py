"""Timing and performance assertions."""

from __future__ import annotations

from app.services.assertions.base import AssertionContext, AssertionResult, run_safe

DEFAULT_MAX_PAGE_LOAD_MS = 30_000
WAIT_TOLERANCE_MS = 500


def assert_page_load_time(ctx: AssertionContext, max_ms: int = DEFAULT_MAX_PAGE_LOAD_MS) -> AssertionResult:
    """Assert that the page action completed within the allowed load time."""

    def check() -> tuple[bool, str, str, str | None]:
        duration = ctx.action_duration_ms
        passed = duration <= max_ms
        reason = None if passed else f"Page load took {duration}ms, exceeding limit of {max_ms}ms"
        return passed, f"<= {max_ms}ms", f"{duration}ms", reason

    return run_safe("page_load_time", check)


def assert_wait_duration(ctx: AssertionContext) -> AssertionResult:
    """Assert that a wait action elapsed close to the requested duration."""

    def check() -> tuple[bool, str, str, str | None]:
        expected_ms = int(ctx.action.get("ms", 1000))
        actual_ms = ctx.action_duration_ms
        passed = abs(actual_ms - expected_ms) <= WAIT_TOLERANCE_MS + expected_ms * 0.2
        reason = None if passed else f"Wait took {actual_ms}ms, expected ~{expected_ms}ms"
        return passed, f"~{expected_ms}ms", f"{actual_ms}ms", reason

    return run_safe("wait_duration", check)
