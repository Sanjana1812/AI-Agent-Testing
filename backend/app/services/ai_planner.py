from __future__ import annotations

import json
import logging
import re

from app.config import settings
from app.services.ollama_client import generate_plan
from app.services.ollama_health import is_ollama_available

logger = logging.getLogger(__name__)

ALLOWED_ACTIONS = frozenset(
    {
        "open_page",
        "wait",
        "click",
        "scroll",
        "fill",
        "verify_visible",
        "verify_text",
        "verify_form",
        "capture",
    }
)
ALLOWED_TARGETS = frozenset(
    {
        "navigation",
        "menu",
        "header",
        "footer",
        "hero",
        "section",
        "button",
        "submit",
        "form",
        "input",
        "email",
        "password",
        "link",
        "image",
    }
)
MIN_STEPS = 4
MAX_STEPS = 8

TARGET_ACTIONS = frozenset({"click", "scroll", "fill", "verify_visible", "verify_form"})

GENERIC_TARGETS = frozenset({"page", "text", "body", "content", "main", "visible"})
FORBIDDEN_VERIFY_TEXT_INTENTS = frozenset(
    {"flow", "navigation", "login", "signup", "contact", "form", "search", "checkout", "dashboard", "profile", "general"}
)

INTENTS = (
    "navigation",
    "flow",
    "login",
    "signup",
    "contact",
    "form",
    "search",
    "checkout",
    "dashboard",
    "profile",
    "responsive",
    "accessibility",
    "performance",
    "general",
)

INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "navigation": ("navigation", "navbar", "nav bar", "nav menu", "top menu", "site menu", "menu bar"),
    "flow": ("flow", "journey", "entire website", "whole site", "full site", "user flow", "end to end", "e2e", "website flow"),
    "login": ("login", "log in", "sign in", "sign-in", "authenticate", "authentication"),
    "signup": ("signup", "sign up", "sign-up", "register", "registration", "create account"),
    "contact": ("contact", "contact us", "contact form", "get in touch", "reach us"),
    "form": ("form validation", "validate form", "submit form", "fill form", "web form"),
    "search": ("search", "search bar", "search box", "lookup", "find product"),
    "checkout": ("checkout", "check out", "shopping cart", "cart", "purchase", "buy now", "payment"),
    "dashboard": ("dashboard", "admin panel", "control panel", "overview page"),
    "profile": ("profile", "my account", "account page", "user profile", "settings page"),
    "responsive": ("responsive", "mobile view", "mobile layout", "tablet", "viewport", "breakpoints"),
    "accessibility": ("accessibility", "a11y", "wcag", "screen reader", "aria"),
    "performance": ("performance", "page speed", "load time", "loading speed", "lighthouse"),
}

LEGACY_SELECTOR_TO_TARGET = {
    "nav": "navigation",
    "navbar": "navigation",
    "nav_bar": "navigation",
    "navigation": "navigation",
    "menu": "menu",
    "header": "header",
    "footer": "footer",
    "hero": "hero",
    "hero_section": "hero",
    "section": "section",
    "main_content": "section",
    "content": "section",
    "main": "section",
    "cta": "button",
    "cta_button": "button",
    "button": "button",
    "submit": "submit",
    "form": "form",
    "input": "input",
    "email": "email",
    "password": "password",
    "link": "link",
    "social": "link",
    "social_links": "link",
    "img": "image",
    "image": "image",
    "background": "image",
    "cards": "section",
    "card": "section",
    "dashboard": "section",
    "success": "section",
    "search": "input",
    "search_box": "input",
}


def detect_intent(goal: str) -> str:
    goal_lower = goal.lower().strip()
    if not goal_lower:
        return "general"

    best_intent = "general"
    best_score = 0

    for intent, keywords in INTENT_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in goal_lower)
        if score > best_score:
            best_score = score
            best_intent = intent

    if best_score == 0:
        if "hero" in goal_lower:
            return "flow"
        if "footer" in goal_lower:
            return "navigation"
        if "form" in goal_lower:
            return "form"

    return best_intent


def _plan(*steps: dict) -> list[dict]:
    plan = list(steps)
    if not plan or plan[-1]["action"] != "capture":
        plan.append({"action": "capture"})
    return plan[:MAX_STEPS]


INTENT_PLANS: dict[str, list[dict]] = {
    "navigation": _plan(
        {"action": "open_page"},
        {"action": "wait", "ms": 800},
        {"action": "verify_visible", "target": "navigation"},
        {"action": "click", "target": "link"},
        {"action": "wait", "ms": 800},
        {"action": "verify_visible", "target": "header"},
    ),
    "flow": _plan(
        {"action": "open_page"},
        {"action": "verify_visible", "target": "navigation"},
        {"action": "verify_visible", "target": "hero"},
        {"action": "scroll", "target": "section"},
        {"action": "verify_visible", "target": "section"},
        {"action": "verify_visible", "target": "footer"},
    ),
    "login": _plan(
        {"action": "open_page"},
        {"action": "verify_visible", "target": "form"},
        {"action": "fill", "target": "email", "value": "test@example.com"},
        {"action": "fill", "target": "password", "value": "password123"},
        {"action": "click", "target": "submit"},
        {"action": "wait", "ms": 1000},
        {"action": "verify_visible", "target": "section"},
    ),
    "signup": _plan(
        {"action": "open_page"},
        {"action": "verify_visible", "target": "form"},
        {"action": "verify_form", "target": "form"},
        {"action": "fill", "target": "email", "value": "user@example.com"},
        {"action": "fill", "target": "password", "value": "Password123!"},
        {"action": "click", "target": "submit"},
        {"action": "wait", "ms": 1000},
    ),
    "contact": _plan(
        {"action": "open_page"},
        {"action": "verify_visible", "target": "form"},
        {"action": "verify_form", "target": "form"},
        {"action": "fill", "target": "input", "value": "QA Tester"},
        {"action": "fill", "target": "email", "value": "qa@example.com"},
        {"action": "click", "target": "submit"},
        {"action": "wait", "ms": 1000},
    ),
    "form": _plan(
        {"action": "open_page"},
        {"action": "verify_visible", "target": "form"},
        {"action": "verify_form", "target": "form"},
        {"action": "fill", "target": "input", "value": "test value"},
        {"action": "click", "target": "submit"},
        {"action": "wait", "ms": 800},
    ),
    "search": _plan(
        {"action": "open_page"},
        {"action": "verify_visible", "target": "input"},
        {"action": "fill", "target": "input", "value": "test query"},
        {"action": "click", "target": "button"},
        {"action": "wait", "ms": 1000},
        {"action": "verify_visible", "target": "section"},
    ),
    "checkout": _plan(
        {"action": "open_page"},
        {"action": "verify_visible", "target": "button"},
        {"action": "click", "target": "button"},
        {"action": "verify_visible", "target": "form"},
        {"action": "fill", "target": "email", "value": "buyer@example.com"},
        {"action": "click", "target": "submit"},
        {"action": "wait", "ms": 1000},
    ),
    "dashboard": _plan(
        {"action": "open_page"},
        {"action": "verify_visible", "target": "navigation"},
        {"action": "verify_visible", "target": "section"},
        {"action": "verify_visible", "target": "header"},
        {"action": "click", "target": "link"},
        {"action": "wait", "ms": 800},
    ),
    "profile": _plan(
        {"action": "open_page"},
        {"action": "verify_visible", "target": "navigation"},
        {"action": "click", "target": "link"},
        {"action": "verify_visible", "target": "form"},
        {"action": "verify_visible", "target": "section"},
        {"action": "wait", "ms": 800},
    ),
    "responsive": _plan(
        {"action": "open_page"},
        {"action": "verify_visible", "target": "navigation"},
        {"action": "verify_visible", "target": "hero"},
        {"action": "scroll", "target": "section"},
        {"action": "verify_visible", "target": "footer"},
    ),
    "accessibility": _plan(
        {"action": "open_page"},
        {"action": "verify_visible", "target": "navigation"},
        {"action": "verify_visible", "target": "header"},
        {"action": "click", "target": "link"},
        {"action": "verify_visible", "target": "form"},
        {"action": "wait", "ms": 800},
    ),
    "performance": _plan(
        {"action": "open_page"},
        {"action": "wait", "ms": 2000},
        {"action": "verify_visible", "target": "hero"},
        {"action": "scroll", "target": "section"},
        {"action": "verify_visible", "target": "footer"},
    ),
    "general": _plan(
        {"action": "open_page"},
        {"action": "verify_visible", "target": "navigation"},
        {"action": "verify_visible", "target": "hero"},
        {"action": "scroll", "target": "section"},
        {"action": "verify_visible", "target": "footer"},
    ),
}


def deterministic_fallback(goal: str) -> list[dict]:
    intent = detect_intent(goal)
    goal_lower = goal.lower()

    if "hero" in goal_lower and intent not in ("login", "signup", "contact", "form"):
        return _plan(
            {"action": "open_page"},
            {"action": "verify_visible", "target": "hero"},
            {"action": "verify_visible", "target": "button"},
            {"action": "verify_visible", "target": "image"},
        )

    if "footer" in goal_lower and intent not in ("login", "signup"):
        return _plan(
            {"action": "open_page"},
            {"action": "scroll", "target": "footer"},
            {"action": "verify_visible", "target": "footer"},
            {"action": "click", "target": "link"},
            {"action": "wait", "ms": 800},
        )

    return list(INTENT_PLANS[intent])


def _normalize_target(step: dict) -> str | None:
    if "target" in step and step["target"]:
        target = str(step["target"]).strip().lower().replace("-", "_").replace(" ", "_")
        if target in GENERIC_TARGETS or target == "page":
            return None
        mapped = LEGACY_SELECTOR_TO_TARGET.get(target)
        if mapped:
            return mapped
        return target if target in ALLOWED_TARGETS else None

    selector = step.get("selector")
    if selector:
        key = str(selector).strip().lower().replace("-", "_").replace(" ", "_")
        mapped = LEGACY_SELECTOR_TO_TARGET.get(key)
        if mapped:
            return mapped
        return key if key in ALLOWED_TARGETS else None

    return None


def _parse_json_response(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    return json.loads(cleaned)


def _finalize_plan(plan: list[dict]) -> list[dict]:
    if not plan:
        raise ValueError("Plan is empty")

    if plan[-1]["action"] != "capture":
        plan = [*plan, {"action": "capture"}]

    return plan[:MAX_STEPS]


def _meaningful_target_count(plan: list[dict]) -> int:
    meaningful = 0
    for step in plan:
        action = step.get("action")
        if action in {"click", "scroll", "fill", "verify_visible", "verify_form"}:
            target = step.get("target")
            if target and target not in GENERIC_TARGETS:
                meaningful += 1
    return meaningful


def _is_generic_plan(plan: list[dict], intent: str) -> bool:
    if _meaningful_target_count(plan) < 2:
        return True

    targets = {step.get("target") for step in plan if step.get("target")}
    if targets & GENERIC_TARGETS:
        return True

    actions = [step.get("action") for step in plan]
    if actions.count("verify_text") >= 1 and intent in FORBIDDEN_VERIFY_TEXT_INTENTS:
        return True

    generic_pattern = {"open_page", "verify_visible", "verify_text", "wait", "capture"}
    if set(actions).issubset(generic_pattern) and _meaningful_target_count(plan) < 3:
        return True

    unique_targets = {t for t in targets if t in ALLOWED_TARGETS}
    if len(unique_targets) < 2 and intent in {"flow", "navigation", "general"}:
        return True

    return False


def _validate_plan(plan: list, intent: str) -> list:
    if not plan or not isinstance(plan, list):
        raise ValueError("Plan must be a non-empty list")

    validated: list[dict] = []
    for step in plan[:MAX_STEPS]:
        if not isinstance(step, dict):
            raise ValueError("Each plan step must be an object")

        action = step.get("action")
        if action not in ALLOWED_ACTIONS:
            raise ValueError(f"Unsupported action: {action}")

        entry: dict = {"action": action}

        if action == "verify_text":
            if intent in FORBIDDEN_VERIFY_TEXT_INTENTS:
                raise ValueError("verify_text is not allowed for this intent")
            text = step.get("text")
            if not text:
                raise ValueError("verify_text requires text")
            entry["text"] = str(text)
            validated.append(entry)
            continue

        if action in TARGET_ACTIONS:
            target = _normalize_target(step)
            if not target or target not in ALLOWED_TARGETS:
                raise ValueError(f"Invalid or generic target for {action}: {step}")
            entry["target"] = target

        if action == "fill":
            entry["value"] = str(step.get("value", "test@example.com"))

        if action == "wait":
            entry["ms"] = int(step.get("ms", 1000))

        validated.append(entry)

    validated = _finalize_plan(validated)

    if len(validated) < MIN_STEPS:
        raise ValueError(f"Plan must contain at least {MIN_STEPS} steps")

    if any(step.get("target") in GENERIC_TARGETS for step in validated):
        raise ValueError("Generic page/text targets are not allowed")

    if _is_generic_plan(validated, intent):
        raise ValueError("Plan is too generic")

    return validated


async def generate_test_plan(url: str, goal: str) -> dict:
    intent = detect_intent(goal)
    logger.info("[Planner] Detected intent: %s", intent)
    logger.info("[Planner] Checking Ollama...")

    if await is_ollama_available():
        logger.info("[Planner] Ollama Available")
        logger.info("[Planner] Generating plan with %s for intent=%s", settings.model_name, intent)
        try:
            result = await generate_plan(url, goal, intent)
            if result.success:
                data = _parse_json_response(result.text)
                plan = _validate_plan(data.get("plan", []), intent)
                return {"plan": plan, "source": "ollama", "intent": intent}
            logger.warning("[Planner] Ollama generation failed: %s", result.error)
        except Exception as exc:
            logger.warning("[Planner] Ollama plan parsing failed: %s", exc)
    else:
        logger.warning("[Planner] Ollama unavailable")

    logger.info("[Planner] Using intent-based fallback for intent=%s", intent)
    return {"plan": deterministic_fallback(goal), "source": "fallback", "intent": intent}
