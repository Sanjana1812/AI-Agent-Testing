"""Journey-level assertions run after the full plan executes."""

from __future__ import annotations

from app.services.assertions.base import AssertionContext, AssertionResult, run_safe
from app.services.assertions import element_assertion, page_assertion
from app.services.semantic_targets import SEMANTIC_TARGET_SELECTORS


def _count_locator(ctx: AssertionContext, selector: str) -> int:
    try:
        return ctx.page.locator(selector).count()
    except Exception:
        return 0


def assert_headings_present(ctx: AssertionContext) -> AssertionResult:
    def check() -> tuple[bool, str, str, str | None]:
        count = _count_locator(ctx, "h1, h2")
        passed = count > 0
        actual = f"{count} heading(s)"
        reason = None if passed else "No h1/h2 headings found on the page"
        return passed, "headings present", actual, reason

    return run_safe("headings_present", check)


def assert_buttons_present(ctx: AssertionContext) -> AssertionResult:
    def check() -> tuple[bool, str, str, str | None]:
        count = _count_locator(ctx, "button, [role='button'], input[type='submit'], a[href]:visible")
        passed = count > 0
        actual = f"{count} button(s)"
        reason = None if passed else "No interactive buttons found"
        return passed, "buttons present", actual, reason

    return run_safe("buttons_present", check)


def assert_forms_present(ctx: AssertionContext) -> AssertionResult:
    def check() -> tuple[bool, str, str, str | None]:
        count = _count_locator(ctx, "form")
        if count == 0:
            return True, "forms present", "0 form(s) — optional on this page", None
        actual = f"{count} form(s)"
        return True, "forms present", actual, None

    return run_safe("forms_present", check)


def assert_navigation_present(ctx: AssertionContext) -> AssertionResult:
    def check() -> tuple[bool, str, str, str | None]:
        count = _count_locator(ctx, "nav a, header a, [role='navigation'] a, main a[href], a[href]:visible")
        passed = count > 0
        actual = f"{count} navigation link(s)"
        reason = None if passed else "No navigation links found"
        return passed, "navigation present", actual, reason

    return run_safe("navigation_present", check)


def run_final_journey_assertions(ctx: AssertionContext) -> list:
    """Run structural assertions on the final page state."""
    results: list = [
        page_assertion.assert_page_title_exists(ctx),
        assert_headings_present(ctx),
        assert_buttons_present(ctx),
        assert_forms_present(ctx),
        assert_navigation_present(ctx),
    ]
    for target in ("hero", "footer"):
        selector = SEMANTIC_TARGET_SELECTORS.get(target)
        if selector and _count_locator(ctx, selector) > 0:
            results.append(element_assertion.assert_element_visible(ctx, target))
    return results
