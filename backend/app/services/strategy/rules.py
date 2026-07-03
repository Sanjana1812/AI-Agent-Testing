"""Strategy rules by website archetype (Sprint 4.1A)."""

from __future__ import annotations

EXECUTION_FLOWS: dict[str, list[str]] = {
    "Hospital": ["Homepage", "Doctors", "Appointment", "Contact", "Screenshot"],
    "SaaS": ["Homepage", "Features", "Pricing", "Sign Up", "Screenshot"],
    "Ecommerce": ["Homepage", "Search", "Product", "Cart", "Screenshot"],
    "Portfolio": ["Homepage", "Projects", "About", "Contact", "Screenshot"],
    "Authentication Portal": ["Homepage", "Login", "Sign Up", "Screenshot"],
    "Documentation": ["Homepage", "Docs", "API", "Search", "Screenshot"],
    "Contact / Lead Generation": ["Homepage", "Services", "Contact", "Screenshot"],
    "Marketing Website": ["Homepage", "About", "Services", "Contact", "Screenshot"],
    "Business Website": ["Homepage", "About", "Services", "Contact", "Screenshot"],
}

STRATEGY_TEMPLATES: dict[str, str] = {
    "Hospital": "Validate care-access journeys: doctor discovery, appointment booking, and emergency contact paths.",
    "SaaS": "Prioritize evaluation funnel: feature discovery, pricing transparency, and sign-up conversion.",
    "Ecommerce": "Focus on product discovery, cart persistence, and checkout readiness.",
    "Portfolio": "Exercise showcase navigation, project galleries, and contact conversion.",
    "Authentication Portal": "Stress credential flows: login, registration, and account recovery surfaces.",
    "Documentation": "Cover documentation navigation, search, and reference content accessibility.",
    "Contact / Lead Generation": "Validate lead-capture CTAs, contact forms, and service discovery.",
    "Marketing Website": "Test primary navigation depth, hero messaging, and conversion CTAs.",
    "Business Website": "Verify service discovery, trust signals, and contact pathways.",
}

EXECUTION_PRIORITIES: dict[str, list[str]] = {
    "Hospital": ["Navigation", "Doctor Search", "Appointment", "Forms", "Footer"],
    "SaaS": ["Hero", "Features", "Pricing", "Sign Up", "Documentation"],
    "Ecommerce": ["Search", "Navigation", "Product", "Cart", "Checkout"],
    "Portfolio": ["Hero", "Projects", "About", "Contact", "Navigation"],
    "Authentication Portal": ["Login", "Sign Up", "Password Reset", "Forms", "Navigation"],
    "Documentation": ["Search", "Navigation", "Documentation", "Sidebar", "Footer"],
    "Contact / Lead Generation": ["Hero", "Contact", "Forms", "CTA", "Footer"],
    "Marketing Website": ["Hero", "Navigation", "CTA", "Contact", "Forms"],
    "Business Website": ["Hero", "Navigation", "Services", "Contact", "Footer"],
}
