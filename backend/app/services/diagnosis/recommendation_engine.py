"""Generate evidence-driven recommendations and next steps."""

from __future__ import annotations

from typing import Any

from app.services.diagnosis.models import FailureType, Ownership, SeverityLevel
from app.services.diagnosis.prompts import BUSINESS_IMPACT_TEMPLATES


def _website_type(evidence_package: dict[str, Any]) -> str:
    analysis = evidence_package.get("website_analysis") or {}
    return str(
        analysis.get("website_type")
        or (evidence_package.get("planner_metadata") or {}).get("website_type")
        or "web application"
    )


def _business_domain(evidence_package: dict[str, Any]) -> str:
    analysis = evidence_package.get("website_analysis") or {}
    return str(analysis.get("business_domain") or "general web")


def _strategy_focus(evidence_package: dict[str, Any]) -> str:
    strategy = evidence_package.get("testing_strategy") or {}
    priorities = strategy.get("execution_priority") or strategy.get("testing_priority") or []
    if priorities:
        return str(priorities[0])
    return str(strategy.get("testing_strategy") or "primary user flows")


def build_recommendations(
    failure_type: FailureType,
    severity: SeverityLevel,
    ownership: Ownership,
    evidence_package: dict[str, Any],
    *,
    root_cause: str = "",
    navigation_mapping: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Return developer/QA actions, business impact, and next steps."""
    website_type = _website_type(evidence_package)
    domain = _business_domain(evidence_package)
    focus = _strategy_focus(evidence_package)

    impact_template = BUSINESS_IMPACT_TEMPLATES.get(
        severity.value, BUSINESS_IMPACT_TEMPLATES["MEDIUM"]
    )
    business_impact = impact_template.format(
        website_type=website_type,
        business_domain=domain,
        strategy_focus=focus,
    )

    recommendations: dict[str, dict[str, str | list[str]]] = {
        FailureType.TEST_DESIGN: {
            "recommendation": (
                "Refine planner semantic filtering so low-value controls (shortcuts, "
                "accessibility chrome) are excluded from business journeys."
            ),
            "developer_action": (
                "No application code change required unless the targeted control is "
                "genuinely business-critical."
            ),
            "qa_action": (
                f"Rewrite the test goal and journey to target {focus} instead of "
                "peripheral UI controls. Add assertions on the intended shopping or "
                "conversion path."
            ),
            "next_steps": [
                "Update the test goal to name the business journey explicitly.",
                "Re-run with execution priorities aligned to strategy.",
                "Add journey assertions on checkout, catalog, or sign-up flows.",
            ],
        },
        FailureType.SELECTOR: {
            "recommendation": (
                "Stabilize the locator using role/text semantics or data-testid attributes "
                "observed in the evidence DOM snapshot."
            ),
            "developer_action": (
                "Add stable selectors (data-testid or aria labels) to the target element "
                "if it is business-critical."
            ),
            "qa_action": (
                "Update the plan step selector and add a visibility assertion before interaction."
            ),
            "next_steps": [
                "Compare failure screenshot with DOM snapshot headings.",
                "Promote the working alternative selector if one was attempted.",
                "Re-run on the same viewport recorded in evidence.",
            ],
        },
        FailureType.ASSERTION: {
            "recommendation": (
                "Validate whether the expected state matches current product behavior "
                "using assertion evidence."
            ),
            "developer_action": (
                "If the assertion reflects a product regression, fix the UI state or "
                "copy that diverged from expected."
            ),
            "qa_action": (
                "Confirm expected values against acceptance criteria; update assertions "
                "if requirements changed."
            ),
            "next_steps": [
                "Review assertion_results in the evidence package.",
                "Capture a baseline screenshot after fix.",
                "Add a negative assertion if the defect is intermittent.",
            ],
        },
        FailureType.TIMING: {
            "recommendation": (
                "Increase wait strategy for slow-loading content or optimize the critical "
                "render path for the target section."
            ),
            "developer_action": (
                "Investigate LCP and network waterfalls for the failing route."
            ),
            "qa_action": (
                "Add an explicit wait for network idle or a known ready selector before "
                "the failing step."
            ),
            "next_steps": [
                "Check network_logs for slow third-party assets.",
                "Re-run with extended stabilization wait.",
                "Profile page load on the recorded viewport.",
            ],
        },
        FailureType.NETWORK: {
            "recommendation": (
                "Resolve the failing HTTP request or routing rule surfaced in network evidence."
            ),
            "developer_action": (
                "Fix API endpoint, CDN, or reverse-proxy configuration returning errors."
            ),
            "qa_action": (
                "Verify environment URL, auth headers, and API mocks for the test target."
            ),
            "next_steps": [
                "Inspect network_errors in failure evidence.",
                "Confirm http_status and final_url.",
                "Re-test from a clean session.",
            ],
        },
        FailureType.APPLICATION: {
            "recommendation": (
                "Fix the JavaScript error recorded in console evidence before re-running "
                "the journey."
            ),
            "developer_action": (
                "Trace the stack from console_errors and patch the offending component."
            ),
            "qa_action": (
                "Attach console log excerpts to the defect ticket and verify fix on staging."
            ),
            "next_steps": [
                "Reproduce manually at the failure URL.",
                "Add a console-error assertion to catch regressions.",
                "Run smoke on adjacent navigation paths.",
            ],
        },
        FailureType.ENVIRONMENT: {
            "recommendation": (
                "Restore the browser automation environment (Playwright Chromium install "
                "and CI sandbox permissions)."
            ),
            "developer_action": "N/A — infrastructure issue.",
            "qa_action": (
                "Run `python -m playwright install chromium` and confirm headless launch."
            ),
            "next_steps": [
                "Verify Playwright browsers on the runner.",
                "Check disk space under storage/playwright-browsers.",
                "Re-run after environment health check.",
            ],
        },
        FailureType.AUTHENTICATION: {
            "recommendation": (
                "Provide valid credentials or session fixtures for the authenticated journey."
            ),
            "developer_action": (
                "Fix auth/session handling if legitimate users are blocked."
            ),
            "qa_action": (
                "Seed test credentials and add a login pre-step aligned with strategy."
            ),
            "next_steps": [
                "Confirm auth cookies in network logs.",
                "Add a dedicated login plan step.",
                "Re-run with a service account.",
            ],
        },
        FailureType.AI_PLANNING: {
            "recommendation": (
                "Improve planner inputs — refresh website context and tighten strategy "
                "constraints before regenerating the plan."
            ),
            "developer_action": "N/A unless planner targets a broken production feature.",
            "qa_action": (
                "Re-run with a clearer goal and confirm Ollama/provider availability."
            ),
            "next_steps": [
                "Review planner_metadata and confidence_breakdown.",
                "Validate context extraction succeeded.",
                "Regenerate plan with strategy-driven journey.",
            ],
        },
        FailureType.NAVIGATION: {
            "recommendation": (
                "Verify the navigation target exists in the current site map and href "
                "matches extracted context links."
            ),
            "developer_action": (
                "Restore broken routes or update redirects for the target destination."
            ),
            "qa_action": (
                "Update the click target to a link present in website analysis navigation."
            ),
            "next_steps": [
                "Compare planned href with navigation entries in evidence.",
                "Check for client-side router changes.",
                "Re-run after sitemap refresh.",
            ],
        },
    }

    default = {
        "recommendation": (
            "Investigate the primary failure evidence and align the next run with "
            "testing strategy priorities."
        ),
        "developer_action": (
            f"Review the failure with {ownership.value} using supporting evidence."
        ),
        "qa_action": (
            "Tighten the test goal, refresh context, and re-run with assertions on "
            f"{focus}."
        ),
        "next_steps": [
            "Review supporting_evidence in the diagnosis report.",
            "Confirm coverage gaps in the coverage report.",
            "Re-run after applying the recommended action.",
        ],
    }

    payload = recommendations.get(failure_type, default)

    if navigation_mapping:
        payload = dict(payload)
        payload["recommendation"] = navigation_mapping["recommendation"]
        payload["qa_action"] = navigation_mapping["qa_action"]
        payload["next_steps"] = [
            "Update semantic navigation mapping to use landmarks before text selectors.",
            "Regenerate the plan and confirm the navigation step selector is nav or role=navigation.",
            "Re-run on the same URL and verify the navigation step passes.",
        ]

    if root_cause and failure_type == FailureType.TEST_DESIGN:
        payload = dict(payload)
        payload["recommendation"] = (
            f"{payload['recommendation']} Root cause context: {root_cause[:200]}"
        )

    return {
        "business_impact": business_impact,
        "recommendation": str(payload["recommendation"]),
        "developer_action": str(payload["developer_action"]),
        "qa_action": str(payload["qa_action"]),
        "next_steps": list(payload["next_steps"]),
    }
