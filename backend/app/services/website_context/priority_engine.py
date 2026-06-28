"""Priority scoring for classified Website Context elements."""

from __future__ import annotations

from app.services.website_context.element_classifier import ElementClass, SectionSemanticType, is_logo_link

BASE_PRIORITIES: dict[str, int] = {
    "CTA": 100,
    "Primary Navigation": 90,
    "Navigation": 90,
    "Login": 90,
    "Signup": 90,
    "Search": 85,
    "Hero": 80,
    "Contact": 75,
    "Form": 70,
    "Feature": 60,
    "Card": 60,
    "Gallery": 55,
    "Pricing": 55,
    "Testimonial": 50,
    "Footer": 30,
    "Logo": 5,
    "General": 40,
}

SECTION_PRIORITIES: dict[SectionSemanticType, int] = {
    "hero": 80,
    "features": 60,
    "pricing": 55,
    "gallery": 55,
    "contact": 75,
    "testimonial": 50,
    "footer": 30,
    "general": 45,
}


def score_classification(classification: ElementClass | str, *, text: str = "", href: str = "") -> int:
    """Return a priority score for a classified element."""
    if is_logo_link(text, href) or classification == "Logo":
        return BASE_PRIORITIES["Logo"]

    if classification == "Navigation" and text:
        lowered = text.lower()
        if lowered in {"about", "services", "products", "pricing", "contact"}:
            return BASE_PRIORITIES["Primary Navigation"]

    return BASE_PRIORITIES.get(str(classification), BASE_PRIORITIES["General"])


def score_section(semantic_type: SectionSemanticType | str) -> int:
    return SECTION_PRIORITIES.get(str(semantic_type), SECTION_PRIORITIES["general"])


def score_button(button: dict, classification: ElementClass) -> int:
    base = score_classification(classification, text=button.get("text", ""))
    if not button.get("visible", True):
        return max(1, base - 40)
    if button.get("enabled") is False or button.get("disabled"):
        return max(1, base - 30)
    if button.get("type") == "cta":
        return max(base, BASE_PRIORITIES["CTA"])
    return base


def score_nav_link(link: dict, classification: ElementClass) -> int:
    return score_classification(classification, text=link.get("text", ""), href=link.get("href", ""))


def score_form(form: dict, classification: ElementClass) -> int:
    base = score_classification(classification)
    if form.get("visible") is False:
        return max(1, base - 20)
    return base
