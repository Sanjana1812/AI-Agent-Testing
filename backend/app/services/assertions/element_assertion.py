"""Element existence and visibility assertions."""

from __future__ import annotations

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from app.services.assertions.base import AssertionContext, AssertionResult, run_safe
from app.services.semantic_targets import SEMANTIC_TARGET_SELECTORS

TARGET_TIMEOUT_MS = 5_000


def _resolve_selector(target: str) -> str | None:
    return SEMANTIC_TARGET_SELECTORS.get(target)


def assert_element_exists(ctx: AssertionContext, target: str) -> AssertionResult:
    """Assert that a semantic target exists in the DOM."""

    def check() -> tuple[bool, str, str, str | None]:
        selector = _resolve_selector(target)
        if not selector:
            return False, f"target:{target}", "unknown", f"No selector mapping for target '{target}'"
        count = ctx.page.locator(selector).count()
        passed = count > 0
        actual = f"{count} element(s) found"
        reason = None if passed else f"Element '{target}' not found using selector '{selector}'"
        return passed, f"exists:{target}", actual, reason

    return run_safe("element_exists", check)


def assert_element_visible(ctx: AssertionContext, target: str) -> AssertionResult:
    """Assert that a semantic target is visible on the page."""

    def check() -> tuple[bool, str, str, str | None]:
        selector = _resolve_selector(target)
        if not selector:
            return False, f"visible:{target}", "unknown", f"No selector mapping for target '{target}'"
        locator = ctx.page.locator(selector).first
        try:
            locator.wait_for(state="visible", timeout=TARGET_TIMEOUT_MS)
            passed = locator.is_visible()
        except PlaywrightTimeoutError:
            passed = False
        actual = "visible" if passed else "not visible"
        reason = None if passed else f"Element '{target}' is not visible (selector: {selector})"
        return passed, f"visible:{target}", actual, reason

    return run_safe("element_visible", check)
