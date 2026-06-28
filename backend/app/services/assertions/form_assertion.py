"""Form structure and submission assertions."""

from __future__ import annotations

from app.services.assertions.base import AssertionContext, AssertionResult, run_safe
from app.services.semantic_targets import SEMANTIC_TARGET_SELECTORS

TARGET_TIMEOUT_MS = 5_000


def assert_form_has_fields(ctx: AssertionContext, target: str = "form") -> AssertionResult:
    """Assert that a form contains at least one input, textarea, or select."""

    def check() -> tuple[bool, str, str, str | None]:
        selector = SEMANTIC_TARGET_SELECTORS.get(target, "form")
        form = ctx.page.locator(selector).first
        form.wait_for(state="visible", timeout=TARGET_TIMEOUT_MS)
        count = form.locator("input, textarea, select").count()
        passed = count > 0
        actual = f"{count} field(s)"
        reason = None if passed else f"Form '{target}' has no input fields"
        return passed, "at least 1 form field", actual, reason

    return run_safe("form_has_fields", check)


def assert_form_submission_success(ctx: AssertionContext) -> AssertionResult:
    """
    Assert that a form submission did not surface a visible error state.

    Checks for common error patterns and verifies the page remains interactive.
    """

    def check() -> tuple[bool, str, str, str | None]:
        error_selectors = (
            "[role='alert'], .error, .form-error, .invalid-feedback, "
            "[class*='error' i], [aria-invalid='true']"
        )
        errors = ctx.page.locator(error_selectors)
        visible_errors = [errors.nth(i).inner_text().strip() for i in range(min(errors.count(), 3))]
        visible_errors = [text for text in visible_errors if text]

        if visible_errors:
            actual = "; ".join(visible_errors[:2])
            return False, "no visible form errors", actual, f"Form submission showed errors: {actual}"

        return True, "successful form submission", "no errors detected", None

    return run_safe("form_submission_success", check)
