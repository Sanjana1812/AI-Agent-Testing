"""Text content assertions."""

from __future__ import annotations

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from app.services.assertions.base import AssertionContext, AssertionResult, run_safe

TARGET_TIMEOUT_MS = 5_000


def assert_text_equals(ctx: AssertionContext, expected: str) -> AssertionResult:
    """Assert that the page body text equals the expected value."""

    def check() -> tuple[bool, str, str, str | None]:
        actual = ctx.page.locator("body").inner_text().strip()
        passed = actual == expected
        reason = None if passed else f"Page text does not equal '{expected}'"
        return passed, expected, actual[:500], reason

    return run_safe("text_equals", check)


def assert_text_contains(ctx: AssertionContext, expected: str) -> AssertionResult:
    """Assert that visible text containing *expected* is present on the page."""

    def check() -> tuple[bool, str, str, str | None]:
        try:
            locator = ctx.page.get_by_text(expected, exact=False).first
            locator.wait_for(state="visible", timeout=TARGET_TIMEOUT_MS)
            passed = True
            actual = expected
        except PlaywrightTimeoutError:
            passed = False
            actual = "text not found"
        reason = None if passed else f"Text '{expected}' was not found on the page"
        return passed, f"contains:{expected}", actual, reason

    return run_safe("text_contains", check)
