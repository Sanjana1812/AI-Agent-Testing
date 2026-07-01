"""Risk and testing priority engine by website archetype (Sprint 4.1)."""

from __future__ import annotations

from app.services.planner.context_index import ContextIndex
from app.services.website_context.json_builder import WebsiteContext

DEFAULT_PRIORITIES: dict[str, list[str]] = {
    "Hospital": ["Appointment", "Doctor Search", "Navigation", "Forms", "Footer"],
    "SaaS": ["Pricing", "Sign Up", "Documentation", "Features", "Contact"],
    "Ecommerce": ["Product", "Cart", "Checkout", "Login", "Search"],
    "Portfolio": ["Projects", "Contact", "About", "Navigation", "Forms"],
    "Authentication Portal": ["Login", "Sign Up", "Password Reset", "Session", "Navigation"],
    "Documentation": ["Search", "Navigation", "API Reference", "Code Samples", "Sidebar"],
    "Contact / Lead Generation": ["Contact Form", "CTA", "Navigation", "Validation", "Footer"],
    "Marketing Website": ["Navigation", "CTA", "Contact", "Hero", "Forms"],
    "Business Website": ["Navigation", "Contact", "Forms", "CTA", "Footer"],
}

DEFAULT_RISK_AREAS: dict[str, list[str]] = {
    "Hospital": ["Appointment booking", "Doctor search", "Emergency contact", "Patient forms"],
    "SaaS": ["Pricing accuracy", "Sign-up flow", "Trial conversion", "Documentation search"],
    "Ecommerce": ["Product discovery", "Cart persistence", "Checkout payment", "Inventory display"],
    "Portfolio": ["Project gallery", "Contact form", "Resume/download links"],
    "Authentication Portal": ["Credential validation", "Session handling", "Account recovery"],
    "Documentation": ["Search relevance", "Versioned docs", "Broken anchor links"],
    "Contact / Lead Generation": ["Form submission", "Spam protection", "CTA visibility"],
    "Marketing Website": ["Primary CTA", "Navigation depth", "Mobile layout"],
    "Business Website": ["Service discovery", "Contact pathways", "Trust signals"],
}


def _has_login_form(index: ContextIndex) -> bool:
    if index.has_password_field():
        return True
    return any(
        str(form.get("classification", "")).lower() == "login"
        for form in index.context.get("forms", [])
    )


def _has_contact_form(index: ContextIndex) -> bool:
    return any(
        str(form.get("classification", "")).lower() in {"contact", "lead", "inquiry"}
        for form in index.context.get("forms", [])
    )


def _context_risk_signals(index: ContextIndex) -> list[str]:
    signals: list[str] = []
    if _has_login_form(index):
        signals.append("Authentication forms")
    if len(index.context.get("forms", [])) >= 2:
        signals.append("Multiple form workflows")
    if index.usable_buttons() and any(
        "pricing" in str(button.get("text", "")).lower() for button in index.usable_buttons()
    ):
        signals.append("Pricing interactions")
    if len(index.context.get("navigation", [])) >= 6:
        signals.append("Deep navigation tree")
    if not index.usable_buttons() and not index.context.get("navigation"):
        signals.append("Sparse interactive surface")
    return signals


def compute_testing_priority(website_type: str, *, context: WebsiteContext | None = None) -> list[str]:
    base = list(DEFAULT_PRIORITIES.get(website_type, DEFAULT_PRIORITIES["Business Website"]))
    if context is None:
        return base
    index = ContextIndex(context)
    if _has_login_form(index) and "Login" not in base:
        base.insert(0, "Login")
    if _has_contact_form(index) and "Contact" not in base[:3]:
        base.insert(min(2, len(base)), "Contact")
    return base[:6]


def compute_high_risk_areas(
    website_type: str,
    *,
    context: WebsiteContext | None = None,
) -> list[str]:
    risks = list(DEFAULT_RISK_AREAS.get(website_type, DEFAULT_RISK_AREAS["Business Website"]))
    if context is None:
        return risks
    index = ContextIndex(context)
    for signal in _context_risk_signals(index):
        if signal not in risks:
            risks.append(signal)
    return risks[:8]
