"""Semantic element classification for Website Context."""

from __future__ import annotations

import re
from typing import Literal

ElementClass = Literal[
    "Hero",
    "CTA",
    "Navigation",
    "Footer",
    "Form",
    "Login",
    "Signup",
    "Card",
    "Gallery",
    "Feature",
    "Contact",
    "Pricing",
    "Testimonial",
    "Logo",
    "Search",
    "General",
]

SectionSemanticType = Literal[
    "hero",
    "features",
    "pricing",
    "footer",
    "gallery",
    "contact",
    "testimonial",
    "general",
]

ButtonType = Literal["cta", "primary", "secondary", "icon", "submit", "general"]

LOGO_TEXT = frozenset({"home", "logo", "brand"})
CTA_PHRASES = (
    "get started",
    "let's talk",
    "lets talk",
    "sign up",
    "buy now",
    "contact us",
    "try free",
    "book a demo",
    "learn more",
    "subscribe",
)
PRIMARY_CLASSES = ("primary", "btn-primary", "cta", "button--primary")
ICON_HINTS = ("icon", "svg", "menu-toggle", "hamburger")


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def is_logo_link(text: str, href: str) -> bool:
    normalized = _normalize(text)
    if normalized in LOGO_TEXT:
        return True
    if href in {"/", "#", ""} and len(normalized) <= 12:
        return True
    return "logo" in normalized


def classify_nav_link(link: dict) -> ElementClass:
    text = _normalize(link.get("text", ""))
    href = link.get("href", "")
    if is_logo_link(text, href):
        return "Logo"
    if any(word in text for word in ("login", "sign in", "log in")):
        return "Login"
    if any(word in text for word in ("sign up", "signup", "register")):
        return "Signup"
    if "search" in text:
        return "Search"
    section = link.get("section", "")
    if section == "footer":
        return "Footer"
    return "Navigation"


def classify_button(button: dict) -> ElementClass:
    text = _normalize(button.get("text", ""))
    classes = _normalize(button.get("class_name", ""))
    section = button.get("section", "")

    if is_logo_link(text, ""):
        return "Logo"
    if any(phrase in text for phrase in CTA_PHRASES):
        return "CTA"
    if any(word in text for word in ("login", "sign in")):
        return "Login"
    if any(word in text for word in ("sign up", "signup", "register")):
        return "Signup"
    if "search" in text:
        return "Search"
    if section == "footer":
        return "Footer"
    if any(token in classes for token in PRIMARY_CLASSES):
        return "CTA"
    return "General"


def infer_button_type(button: dict, classification: ElementClass) -> ButtonType:
    text = _normalize(button.get("text", ""))
    classes = _normalize(button.get("class_name", ""))
    role = _normalize(button.get("role", ""))

    if classification == "CTA":
        return "cta"
    if role == "submit" or button.get("tag") == "submit":
        return "submit"
    if any(token in classes for token in ICON_HINTS) or len(text) <= 2:
        return "icon"
    if any(token in classes for token in PRIMARY_CLASSES):
        return "primary"
    if classification in {"Login", "Signup", "Search"}:
        return "primary"
    if "secondary" in classes:
        return "secondary"
    return "general"


def classify_form(form: dict) -> ElementClass:
    fields = form.get("fields", [])
    field_types = {str(f.get("type", "")).lower() for f in fields}
    names = " ".join(str(f.get("name", "")).lower() for f in fields)
    placeholders = " ".join(str(f.get("placeholder", "")).lower() for f in fields)
    blob = f"{names} {placeholders}"

    has_password = "password" in field_types
    has_email = "email" in field_types
    has_textarea = "textarea" in field_types

    if has_password and any(word in blob for word in ("login", "sign in", "log in")):
        return "Login"
    if has_password and has_email and any(word in blob for word in ("signup", "register", "sign up")):
        return "Signup"
    if has_textarea or any(word in blob for word in ("contact", "message", "inquiry")):
        return "Contact"
    if "search" in blob:
        return "Search"
    return "Form"


def classify_section(section: dict, *, index: int = 0) -> SectionSemanticType:
    heading = _normalize(section.get("heading", ""))
    class_name = _normalize(section.get("class_name", ""))
    element_id = _normalize(section.get("id", ""))
    tag = _normalize(section.get("tag", ""))
    viewport_top = int(section.get("viewport_top", 9999))
    blob = f"{heading} {class_name} {element_id}"

    if tag == "footer" or "footer" in blob:
        return "footer"
    if (
        index == 0
        or "hero" in blob
        or section.get("role") == "banner"
        or viewport_top <= 120
        or "landing" in blob
        or "jumbotron" in blob
    ):
        return "hero"
    if any(word in blob for word in ("pricing", "price", "plan")):
        return "pricing"
    if any(word in blob for word in ("contact", "reach us", "get in touch")):
        return "contact"
    if any(word in blob for word in ("gallery", "portfolio")):
        return "gallery"
    if any(word in blob for word in ("testimonial", "review", "quote")):
        return "testimonial"
    if any(word in blob for word in ("feature", "benefit", "service")):
        return "features"
    return "general"


def classify_heading(heading: dict, *, index: int = 0) -> ElementClass:
    if heading.get("level") == 1 or index == 0:
        return "Hero"
    text = _normalize(heading.get("text", ""))
    if any(word in text for word in ("pricing", "plan")):
        return "Pricing"
    if any(word in text for word in ("contact", "reach")):
        return "Contact"
    if any(word in text for word in ("feature", "benefit")):
        return "Feature"
    if any(word in text for word in ("testimonial", "review")):
        return "Testimonial"
    return "General"


def classify_footer_link(link: dict) -> ElementClass:
    return classify_nav_link({**link, "section": "footer"})


def classify_anchor_link(link: dict) -> ElementClass:
    return classify_nav_link(link)
