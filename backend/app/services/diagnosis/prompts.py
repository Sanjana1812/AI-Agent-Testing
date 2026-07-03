"""Evidence-driven diagnosis prompt templates (rule-based, no LLM required)."""

from __future__ import annotations

ROOT_CAUSE_TEMPLATES: dict[str, str] = {
    "TEST_DESIGN": (
        "The planner selected {target_label}, which is unrelated to the stated goal "
        "({goal}). The application likely behaved correctly; the test design did not "
        "target a business-critical journey."
    ),
    "SELECTOR": (
        "Step {step_number} ({step_name}) attempted selector {selector}, which could "
        "not be resolved on the page at {current_url}."
    ),
    "ASSERTION": (
        "An assertion on step {step_number} ({step_name}) failed: expected {expected}, "
        "observed {actual}."
    ),
    "TIMING": (
        "Step {step_number} ({step_name}) timed out before the target became interactable "
        "at {current_url}."
    ),
    "NETWORK": (
        "Navigation or network activity failed during step {step_number} "
        "({step_name}) at {current_url}."
    ),
    "APPLICATION": (
        "A client-side application error was recorded during step {step_number} "
        "({step_name}): {exception}."
    ),
    "ENVIRONMENT": (
        "The execution environment could not complete browser automation: {exception}."
    ),
    "NAVIGATION": (
        "The planned navigation to {target_label} did not reach the expected destination. "
        "Final URL: {current_url}."
    ),
    "AUTHENTICATION": (
        "Authentication or session state blocked the journey at {current_url} during "
        "step {step_number} ({step_name})."
    ),
    "DATA": (
        "Expected data was missing or inconsistent during step {step_number} ({step_name})."
    ),
    "AI_PLANNING": (
        "The AI planner produced a plan that does not align with website analysis or "
        "testing strategy priorities for a {website_type} site."
    ),
    "UNKNOWN": (
        "Failure at step {step_number} ({step_name}) could not be classified with "
        "high certainty from available evidence."
    ),
}

REASONING_TEMPLATES: dict[str, str] = {
    "TEST_DESIGN": (
        "Website analysis classified this as {website_type} with strategy focus on "
        "{strategy_focus}. The failed interaction ({target_label}) is not among execution "
        "priorities ({execution_priority}). This indicates a test-design gap, not an "
        "application defect."
    ),
    "SELECTOR": (
        "Failure evidence shows selector {selector} was attempted with "
        "{alternative_count} alternatives. DOM snapshot and page title ({page_title}) "
        "suggest the element may have moved, been renamed, or is hidden."
    ),
    "ASSERTION": (
        "Assertion results on the failed step show {assertion_summary}. Coverage for "
        "{coverage_area} was {coverage_status}."
    ),
    "NETWORK": (
        "Network logs contain {network_error_count} error(s). HTTP status at failure "
        "time: {http_status}."
    ),
    "APPLICATION": (
        "Console captured {console_error_count} error(s) near the failure. "
        "This points to client-side application behavior rather than test tooling."
    ),
}

BUSINESS_IMPACT_TEMPLATES: dict[str, str] = {
    "CRITICAL": (
        "Blocks a revenue-critical or authentication path for {website_type} users "
        "in {business_domain}."
    ),
    "HIGH": (
        "Degrades a primary user journey ({strategy_focus}) and may prevent goal "
        "completion for {website_type} visitors."
    ),
    "MEDIUM": (
        "Impacts secondary navigation or content discovery but core flows may still work."
    ),
    "LOW": (
        "Limited user impact; likely affects edge interactions or non-critical UI chrome."
    ),
}
