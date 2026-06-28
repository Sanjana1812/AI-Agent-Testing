"""Page-level assertions."""

from __future__ import annotations

from pathlib import Path

from app.services.assertions.base import AssertionContext, AssertionResult, run_safe


def assert_page_title_exists(ctx: AssertionContext) -> AssertionResult:
    """Assert that the page has a non-empty document title."""

    def check() -> tuple[bool, str, str, str | None]:
        title = ctx.page.title()
        passed = bool(title.strip())
        reason = None if passed else "Page title is empty"
        return passed, "non-empty title", title, reason

    return run_safe("page_title_exists", check)


def assert_screenshot_captured(ctx: AssertionContext) -> AssertionResult:
    """Assert that a screenshot file was written to disk."""

    def check() -> tuple[bool, str, str, str | None]:
        path = ctx.screenshot_path
        if path is None:
            return False, "screenshot file exists", "no path provided", "Screenshot path was not set"
        exists = Path(path).exists() and Path(path).stat().st_size > 0
        actual = str(path) if exists else "file missing"
        reason = None if exists else f"Screenshot was not saved to {path}"
        return exists, "screenshot file exists", actual, reason

    return run_safe("screenshot_captured", check)
