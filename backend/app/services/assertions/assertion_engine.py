"""Orchestrates post-action assertions for Playwright test steps."""

from __future__ import annotations

import logging

from app.services.assertions import (
    element_assertion,
    form_assertion,
    network_assertion,
    page_assertion,
    text_assertion,
    timing_assertion,
    url_assertion,
)
from app.services.assertions.base import AssertionContext, AssertionResult

logger = logging.getLogger(__name__)


class AssertionEngine:
    """
    Runs structured assertions after each Playwright action.

    Assertion suites are selected automatically based on the action type.
    Individual assertion failures are captured with reasons — they never
    raise exceptions to the caller.
    """

    def run_for_action(self, ctx: AssertionContext) -> list[AssertionResult]:
        """Execute all assertions applicable to the completed action."""
        action_type = ctx.action.get("action", "")
        runners = self._assertions_for(action_type, ctx)

        logger.debug(
            "[AssertionEngine] Running %d assertion(s) for action '%s'",
            len(runners),
            action_type,
        )

        results: list[AssertionResult] = []
        for runner in runners:
            result = runner(ctx)
            results.append(result)
            status = "PASS" if result["passed"] else "FAIL"
            logger.debug(
                "[AssertionEngine] %s [%s] expected=%s actual=%s",
                result["type"],
                status,
                result["expected"],
                result["actual"],
            )

        return results

    def _assertions_for(self, action_type: str, ctx: AssertionContext) -> list:
        target = ctx.action.get("target", "")
        text = ctx.action.get("text", "")

        if action_type == "open_page":
            return [
                lambda c: network_assertion.assert_http_status(c),
                lambda c: url_assertion.assert_url_host_matches(c, ctx.url),
                lambda c: page_assertion.assert_page_title_exists(c),
                lambda c: timing_assertion.assert_page_load_time(c),
            ]

        if action_type == "wait":
            return [timing_assertion.assert_wait_duration]

        if action_type == "click":
            assertions = []
            if target:
                assertions.append(lambda c, t=target: element_assertion.assert_element_visible(c, t))
            if target == "submit":
                assertions.append(form_assertion.assert_form_submission_success)
            return assertions or [page_assertion.assert_page_title_exists]

        if action_type == "scroll":
            if target:
                return [lambda c, t=target: element_assertion.assert_element_visible(c, t)]
            return [page_assertion.assert_page_title_exists]

        if action_type == "fill":
            if target:
                return [
                    lambda c, t=target: element_assertion.assert_element_visible(c, t),
                    lambda c, t=target: element_assertion.assert_element_exists(c, t),
                ]
            return [page_assertion.assert_page_title_exists]

        if action_type == "verify_visible":
            if target:
                return [lambda c, t=target: element_assertion.assert_element_visible(c, t)]
            return []

        if action_type == "verify_form":
            return [lambda c, t=target or "form": form_assertion.assert_form_has_fields(c, t)]

        if action_type == "verify_text":
            if text:
                return [lambda c, expected=text: text_assertion.assert_text_contains(c, expected)]
            return []

        if action_type == "capture":
            return [page_assertion.assert_screenshot_captured]

        logger.debug("[AssertionEngine] No assertions defined for action '%s'", action_type)
        return []

    def all_passed(self, results: list[AssertionResult]) -> bool:
        """Return True when every assertion in the list passed."""
        return all(result["passed"] for result in results)

    def failure_reasons(self, results: list[AssertionResult]) -> list[str]:
        """Collect human-readable reasons from failed assertions."""
        return [
            result["reason"] or f"{result['type']} failed"
            for result in results
            if not result["passed"]
        ]
