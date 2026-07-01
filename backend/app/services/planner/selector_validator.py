"""Validate selector quality before attaching to execution plans."""

from __future__ import annotations

import re

from app.services.semantic_targets import SEMANTIC_TARGET_SELECTORS

GENERIC_LITERALS = frozenset(
    {
        "button",
        "a",
        "div",
        "section",
        "span",
        "main",
        "article",
        "input",
        "form",
        "footer",
        "link",
        "navigation",
        "hero",
        "menu",
        "header",
        "body",
        "visible",
    }
)

GENERIC_SEMANTIC_VALUES = {value.lower() for value in SEMANTIC_TARGET_SELECTORS.values()}


def is_generic_selector(selector: str | None) -> bool:
    """Return True when the selector is too broad for deterministic targeting."""
    if not selector or not str(selector).strip():
        return True

    normalized = str(selector).strip().lower()
    if normalized in GENERIC_LITERALS:
        return True
    if normalized in GENERIC_SEMANTIC_VALUES:
        return True
    if re.fullmatch(r"[a-z]+", normalized):
        return True
    if normalized in {'[role="button"]', "[role='button']"}:
        return True

    parts = [part.strip().lower() for part in normalized.split(",")]
    if len(parts) > 1 and all(part in GENERIC_LITERALS or part in GENERIC_SEMANTIC_VALUES for part in parts):
        return True

    return False


def validate_selector(
    selector: str | None,
    *,
    used_selectors: set[str] | None = None,
) -> tuple[bool, str | None]:
    """Return (valid, reason)."""
    if not selector or not str(selector).strip():
        return False, "Empty selector"

    normalized = str(selector).strip()
    key = normalized.lower()

    if is_generic_selector(normalized):
        return False, f"Generic selector rejected: {normalized}"

    if used_selectors is not None and key in used_selectors:
        return False, f"Duplicate selector rejected: {normalized}"

    return True, None


def pick_valid_selector(
    candidates: list[str],
    *,
    used_selectors: set[str] | None = None,
) -> str | None:
    """Return the first candidate that passes validation."""
    for candidate in candidates:
        valid, _ = validate_selector(candidate, used_selectors=used_selectors)
        if valid:
            return candidate
    return None
