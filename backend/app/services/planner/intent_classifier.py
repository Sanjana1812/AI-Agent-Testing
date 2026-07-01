"""Intent classification for journey-aware test planning."""

from __future__ import annotations

import re
from enum import Enum


class IntentType(str, Enum):
    FLOW = "flow"
    NAVIGATION = "navigation"
    LOGIN = "login"
    CONTACT = "contact"
    FORM = "form"
    PURCHASE = "purchase"
    SEARCH = "search"
    UNKNOWN = "unknown"


INTENT_PATTERNS: dict[IntentType, tuple[str, ...]] = {
    IntentType.FLOW: (
        r"\bcheck the flow\b",
        r"\buser flow\b",
        r"\bwebsite flow\b",
        r"\bsite flow\b",
        r"\bentire (website|site)\b",
        r"\bwhole site\b",
        r"\bfull site\b",
        r"\bend to end\b",
        r"\be2e\b",
        r"\bjourney\b",
        r"\bexplore (the )?(site|website)\b",
        r"\bbrowse (the )?(site|website)\b",
        r"\bwalk through\b",
    ),
    IntentType.NAVIGATION: (
        r"\bnavigation\b",
        r"\bnavbar\b",
        r"\bnav bar\b",
        r"\bnav menu\b",
        r"\btop menu\b",
        r"\bsite menu\b",
        r"\bmenu bar\b",
        r"\bverify nav\b",
        r"\btest nav\b",
    ),
    IntentType.LOGIN: (
        r"\blogin\b",
        r"\blog in\b",
        r"\bsign in\b",
        r"\bsign-in\b",
        r"\bauthenticate\b",
        r"\bauthentication\b",
        r"\bsignup\b",
        r"\bsign up\b",
        r"\bregister\b",
        r"\bregistration\b",
        r"\bcreate account\b",
    ),
    IntentType.CONTACT: (
        r"\bcontact us\b",
        r"\bcontact form\b",
        r"\bget in touch\b",
        r"\breach us\b",
        r"\bfill contact\b",
        r"\bsend (a )?message\b",
    ),
    IntentType.FORM: (
        r"\bform validation\b",
        r"\bvalidate form\b",
        r"\bsubmit form\b",
        r"\bfill form\b",
        r"\bweb form\b",
        r"\btest form\b",
    ),
    IntentType.PURCHASE: (
        r"\bbuy\b",
        r"\bpurchase\b",
        r"\bcheckout\b",
        r"\bcheck out\b",
        r"\bshopping cart\b",
        r"\bcart\b",
        r"\bpayment\b",
        r"\border\b",
        r"\badd to cart\b",
    ),
    IntentType.SEARCH: (
        r"\bsearch\b",
        r"\bsearch bar\b",
        r"\bsearch box\b",
        r"\blookup\b",
        r"\bfind (a )?product\b",
        r"\bfind courses\b",
    ),
}

INTENT_KEYWORDS: dict[IntentType, tuple[str, ...]] = {
    IntentType.FLOW: ("flow", "journey", "e2e", "end to end", "whole site", "full site"),
    IntentType.NAVIGATION: ("navigation", "navbar", "nav menu", "menu bar"),
    IntentType.LOGIN: ("login", "log in", "sign in", "signup", "register"),
    IntentType.CONTACT: ("contact", "get in touch", "reach us"),
    IntentType.FORM: ("form", "submit form", "fill form"),
    IntentType.PURCHASE: ("buy", "purchase", "checkout", "cart", "payment"),
    IntentType.SEARCH: ("search", "lookup", "find product", "find courses"),
}


def _normalize_goal(goal: str) -> str:
    return re.sub(r"\s+", " ", goal.lower().strip())


def classify_intent(goal: str) -> IntentType:
    """Classify a natural-language testing goal into an IntentType."""
    normalized = _normalize_goal(goal)
    if not normalized:
        return IntentType.UNKNOWN

    pattern_scores: dict[IntentType, int] = {intent: 0 for intent in IntentType}
    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, normalized):
                pattern_scores[intent] += 2

    for intent, keywords in INTENT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in normalized:
                pattern_scores[intent] += 1

    best_intent = max(
        (intent for intent in IntentType if intent != IntentType.UNKNOWN),
        key=lambda intent: pattern_scores[intent],
    )
    if pattern_scores[best_intent] > 0:
        return best_intent

    if "hero" in normalized:
        return IntentType.FLOW
    if "footer" in normalized:
        return IntentType.NAVIGATION
    if "form" in normalized:
        return IntentType.FORM

    return IntentType.FLOW if len(normalized.split()) <= 4 else IntentType.UNKNOWN


def intent_from_legacy(value: str) -> IntentType:
    """Map legacy string intents to IntentType."""
    mapping = {
        "flow": IntentType.FLOW,
        "navigation": IntentType.NAVIGATION,
        "login": IntentType.LOGIN,
        "signup": IntentType.LOGIN,
        "contact": IntentType.CONTACT,
        "form": IntentType.FORM,
        "checkout": IntentType.PURCHASE,
        "purchase": IntentType.PURCHASE,
        "search": IntentType.SEARCH,
        "general": IntentType.FLOW,
        "unknown": IntentType.UNKNOWN,
    }
    return mapping.get(value.lower().strip(), IntentType.UNKNOWN)


def legacy_intent_string(intent: IntentType) -> str:
    """Return the legacy intent string used by AI prompts and validators."""
    if intent == IntentType.PURCHASE:
        return "checkout"
    if intent == IntentType.UNKNOWN:
        return "flow"
    return intent.value


def detect_intent(goal: str) -> str:
    """Backward-compatible intent string for existing callers."""
    return legacy_intent_string(classify_intent(goal))
