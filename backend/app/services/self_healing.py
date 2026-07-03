"""Self-healing element resolution when primary selectors fail."""

from __future__ import annotations

import difflib
import logging
import re
from typing import Any

from playwright.sync_api import Locator
from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)

HEAL_TIMEOUT_MS = 3_000
FUZZY_THRESHOLD = 0.65


def _normalize(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value).strip().lower())


def _label_text(action: dict) -> str | None:
    label = action.get("label")
    if not label:
        return None
    match = re.search(r'"([^"]+)"', str(label))
    if match:
        return match.group(1).strip()
    cleaned = re.sub(r"^(click|verify|scroll|fill)\s+", "", _normalize(label), flags=re.I)
    return cleaned or None


def _fuzzy_match(expected: str, candidate: str) -> float:
    return difflib.SequenceMatcher(None, _normalize(expected), _normalize(candidate)).ratio()


def _candidate_selectors(action: dict) -> list[str]:
    selectors: list[str] = []
    primary = action.get("selector")
    if primary:
        selectors.append(str(primary))
    for alt in action.get("selector_alternatives") or []:
        if alt and str(alt) not in selectors:
            selectors.append(str(alt))
    href = action.get("href")
    if href:
        escaped = str(href).replace('"', '\\"')
        selectors.append(f'a[href="{escaped}"]')
    return selectors


def _text_healing_locator(page: Page, action: dict) -> Locator | None:
    if action.get("target") == "navigation":
        return None
    label = _label_text(action)
    if not label:
        return None

    tag = "button"
    target = action.get("target")
    if target == "link" or action.get("href"):
        tag = "a"

    try:
        exact = page.locator(f'{tag}:has-text("{label}")').first
        if exact.count() > 0:
            return exact
    except Exception:
        pass

    try:
        for node in page.locator(f"{tag}, [role='button'], [role='link']").all()[:40]:
            try:
                text = node.inner_text(timeout=500)
            except Exception:
                continue
            if _fuzzy_match(label, text) >= FUZZY_THRESHOLD:
                return node
    except Exception:
        return None
    return None


def _aria_healing_locator(page: Page, action: dict) -> Locator | None:
    label = _label_text(action)
    if not label:
        return None
    try:
        locator = page.locator(f'[aria-label*="{label}" i]').first
        if locator.count() > 0:
            return locator
    except Exception:
        return None
    return None


def _role_healing_locator(page: Page, action: dict) -> Locator | None:
    target = action.get("target")
    label = _label_text(action)
    role = "link" if target == "link" else "button"
    try:
        locator = page.get_by_role(role, name=label or None).first
        if locator.count() > 0:
            return locator
    except Exception:
        return None
    return None


def heal_locator(page: Page, action: dict, primary_selector: str | None) -> tuple[Locator | None, str | None]:
    """
    Attempt to recover a missing element using alternate selectors and fuzzy matching.

    Uses planner-provided selector_alternatives before semantic recovery strategies.
    """
    for selector in _candidate_selectors(action):
        try:
            locator = page.locator(selector).first
            locator.wait_for(state="visible", timeout=HEAL_TIMEOUT_MS)
            logger.info("[SelfHealing] Recovered element with alternate selector: %s", selector)
            return locator, selector
        except (PlaywrightTimeoutError, Exception):
            continue

    for strategy, finder in (
        ("fuzzy-text", _text_healing_locator),
        ("aria-label", _aria_healing_locator),
        ("role", _role_healing_locator),
    ):
        locator = finder(page, action)
        if locator is None:
            continue
        try:
            locator.wait_for(state="visible", timeout=HEAL_TIMEOUT_MS)
            logger.info("[SelfHealing] Recovered element via %s for label '%s'", strategy, action.get("label"))
            return locator, strategy
        except (PlaywrightTimeoutError, Exception):
            continue

    return None, None


def attach_healing_metadata(step: dict, alternatives: list[str]) -> dict:
    enriched = dict(step)
    if alternatives:
        enriched["selector_alternatives"] = alternatives[:5]
    return enriched
