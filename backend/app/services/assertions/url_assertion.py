"""URL assertions."""

from __future__ import annotations

from urllib.parse import urlparse

from app.services.assertions.base import AssertionContext, AssertionResult, run_safe


def _normalize_url(value: str) -> str:
    return value.rstrip("/")


def assert_url_equals(ctx: AssertionContext, expected: str) -> AssertionResult:
    """Assert that the current page URL equals the expected value."""

    def check() -> tuple[bool, str, str, str | None]:
        actual = ctx.page.url
        passed = _normalize_url(actual) == _normalize_url(expected)
        reason = None if passed else f"URL mismatch: expected '{expected}', got '{actual}'"
        return passed, expected, actual, reason

    return run_safe("url_equals", check)


def assert_url_contains(ctx: AssertionContext, expected: str) -> AssertionResult:
    """Assert that the current page URL contains the expected fragment."""

    def check() -> tuple[bool, str, str, str | None]:
        actual = ctx.page.url
        passed = expected in actual
        reason = None if passed else f"URL '{actual}' does not contain '{expected}'"
        return passed, f"contains:{expected}", actual, reason

    return run_safe("url_contains", check)


def assert_url_host_matches(ctx: AssertionContext, base_url: str) -> AssertionResult:
    """Assert that the current URL shares the same host as the test base URL."""

    def check() -> tuple[bool, str, str, str | None]:
        expected_host = urlparse(base_url).netloc
        actual_host = urlparse(ctx.page.url).netloc
        passed = bool(expected_host) and expected_host == actual_host
        reason = None if passed else f"Expected host '{expected_host}', got '{actual_host}'"
        return passed, expected_host, actual_host, reason

    return run_safe("url_host_matches", check)
