"""Network and HTTP response assertions."""

from __future__ import annotations

from app.services.assertions.base import AssertionContext, AssertionResult, run_safe


def assert_http_status(ctx: AssertionContext, max_status: int = 399) -> AssertionResult:
    """Assert that the last HTTP response status is within the success range."""

    def check() -> tuple[bool, str, str, str | None]:
        status = ctx.http_status if ctx.http_status is not None else 0
        passed = 200 <= status <= max_status
        reason = None if passed else f"HTTP status {status} is outside the 200–{max_status} range"
        return passed, f"200–{max_status}", str(status), reason

    return run_safe("http_status", check)


def assert_http_status_equals(ctx: AssertionContext, expected: int) -> AssertionResult:
    """Assert that the HTTP response status equals an exact value."""

    def check() -> tuple[bool, str, str, str | None]:
        status = ctx.http_status if ctx.http_status is not None else 0
        passed = status == expected
        reason = None if passed else f"Expected HTTP {expected}, received {status}"
        return passed, str(expected), str(status), reason

    return run_safe("http_status_equals", check)
