"""Semantic filtering layer — reject low-value elements before journey generation."""

from __future__ import annotations

import re
from typing import Any

from app.services.website_context.json_builder import WebsiteContext

IGNORED_LABEL_FRAGMENTS = (
    "skip to content",
    "skip navigation",
    "skip to main",
    "main content",
    "accessibility",
    "screen reader",
    "privacy",
    "terms of",
    "terms and",
    "cookie",
    "copyright",
    "all rights reserved",
    "home logo",
    "site logo",
    "brand logo",
    "facebook",
    "instagram",
    "twitter",
    "linkedin icon",
    "social icon",
    "share on",
    "follow us",
)

IGNORED_EXACT_LABELS = frozenset({"logo", "home", "menu", "close", "×", "x"})

EMAIL_PATTERN = re.compile(r"^mailto:", re.I)
PHONE_PATTERN = re.compile(r"^tel:", re.I)
DOMAIN_ONLY = re.compile(r"^[\w.-]+\.(com|in|org|net|io|co)$", re.I)
SOCIAL_HREF = re.compile(r"(facebook|instagram|twitter|linkedin|youtube|tiktok)", re.I)


def _normalize(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value).strip().lower())


def is_ignored_label(text: str | None) -> bool:
    """Return True when label/text should never become a primary user action."""
    normalized = _normalize(text)
    if not normalized or len(normalized) <= 1:
        return True
    if normalized in IGNORED_EXACT_LABELS:
        return True
    if any(fragment in normalized for fragment in IGNORED_LABEL_FRAGMENTS):
        return True
    if DOMAIN_ONLY.match(normalized):
        return True
    if "@" in normalized or normalized.startswith("mailto:"):
        return True
    if " icon" in normalized or normalized.endswith(" icon"):
        return True
    return False


def is_ignored_href(href: str | None) -> bool:
    if not href:
        return False
    href = href.strip()
    if EMAIL_PATTERN.match(href) or PHONE_PATTERN.match(href):
        return True
    if SOCIAL_HREF.search(href):
        return True
    if href.startswith("#") and len(href) <= 2:
        return True
    return False


def is_decorative_element(element: dict[str, Any]) -> bool:
    """Ignore decorative buttons, empty labels, and footer legal noise."""
    text = _normalize(element.get("text"))
    href = element.get("href", "")
    classification = _normalize(element.get("classification"))

    if is_ignored_label(text):
        return True
    if is_ignored_href(str(href) if href else None):
        return True
    if classification == "logo":
        return True
    if element.get("type") == "icon" and len(text) <= 2:
        return True
    if element.get("visible") is False:
        return True

    section = _normalize(element.get("section"))
    if section == "footer" and any(word in text for word in ("privacy", "terms", "cookie", "legal")):
        return True

    return False


def filter_element_list(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in elements if not is_decorative_element(item)]


def filter_context(context: WebsiteContext) -> WebsiteContext:
    """Remove low-value elements from enriched Website Context."""
    filtered: WebsiteContext = dict(context)
    for key in ("navigation", "buttons", "footer", "links"):
        filtered[key] = filter_element_list(list(context.get(key, [])))  # type: ignore[literal-required]
    return filtered
