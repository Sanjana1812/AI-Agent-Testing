"""Sprint 5.0 — Execution Intelligence prompt templates (reserved for future sprints)."""

from __future__ import annotations

DECISION_REASON_TEMPLATES: dict[str, str] = {
    "CONTINUE": "Step {step_name} completed with status '{status}'. Continue the planned journey.",
    "ABORT": "Step {step_name} failed with status '{status}'. Abort further adaptive actions for this sprint.",
    "RETRY": "Step {step_name} may benefit from a retry (not enabled in Sprint 5.0).",
    "RECOVER": "Step {step_name} may benefit from selector recovery (not enabled in Sprint 5.0).",
    "REPLAN": "Step {step_name} requires a remaining-plan adjustment based on runtime observation.",
    "SKIP": "Step {step_name} may be skippable (not enabled in Sprint 5.0).",
}
