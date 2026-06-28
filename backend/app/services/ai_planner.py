from __future__ import annotations

import json
import logging
import re
import time

from app.config import settings
from app.services.ai.provider_factory import get_ai_provider
from app.services.planner.context_fallback import build_context_plan
from app.services.planner.context_index import ContextIndex
from app.services.planner.context_validator import validate_plan_against_context
from app.services.planner.display_labels import build_step_label
from app.services.planner.plan_metadata import build_plan_metadata, compute_validation_score
from app.services.website_context.json_builder import WebsiteContext, empty_context

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


def _enrich_step_with_context(step: dict, index: ContextIndex) -> dict:
    """Attach highest-priority selectors and human-readable labels."""
    enriched = dict(step)
    action = step.get("action")
    semantic_target = step.get("target")

    if semantic_target in {"button", "submit"} and not enriched.get("selector"):
        btn = index.highest_priority_cta()
        if btn and btn.get("selector"):
            enriched["selector"] = btn["selector"]
            text = btn.get("text") or semantic_target
            if not enriched.get("label"):
                enriched["label"] = build_step_label({"action": action, "target": semantic_target, "text": text})
    elif semantic_target == "link" and not enriched.get("selector"):
        link = index.highest_priority_nav_link() or index.highest_priority_footer_link()
        if link:
            enriched["selector"] = link.get("selector") or (
                f"a[href='{link['href']}']" if link.get("href") else None
            )
            if not enriched.get("label"):
                enriched["label"] = build_step_label(
                    {"action": action, "target": "link", "text": link.get("text", "link")}
                )
    elif semantic_target == "hero" and not enriched.get("label"):
        heading = index.hero_heading()
        enriched["label"] = build_step_label(
            {"action": action, "target": "hero", "text": heading.get("text") if heading else None}
        )
    elif semantic_target == "section" and not enriched.get("label"):
        section = index.highest_priority_section()
        enriched["label"] = build_step_label(
            {
                "action": action,
                "target": "section",
                "semantic_type": section.get("semantic_type") if section else None,
            }
        )
    elif semantic_target == "navigation" and not enriched.get("label"):
        enriched["label"] = build_step_label({"action": action, "target": "navigation"})
    elif semantic_target == "footer" and not enriched.get("label"):
        enriched["label"] = build_step_label({"action": action, "target": "footer"})
    elif semantic_target == "form" and not enriched.get("label"):
        enriched["label"] = build_step_label({"action": action, "target": "form"})

    if not enriched.get("label"):
        enriched["label"] = build_step_label(enriched)

    return enriched


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
            if step.get("target") or step.get("selector"):
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


def _validate_plan(plan: list, intent: str, index: ContextIndex) -> tuple[list, int]:
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
            if not index.supports_text(str(text)):
                raise ValueError(f"Text '{text}' not found in Website Context")
            entry["text"] = str(text)
            validated.append(entry)
            continue

        if action in TARGET_ACTIONS:
            target = _normalize_target(step)
            if not target or target not in ALLOWED_TARGETS:
                raise ValueError(f"Invalid or generic target for {action}: {step}")
            if not index.supports_target(target):
                raise ValueError(f"Target '{target}' not found in Website Context")
            entry["target"] = target
            if step.get("selector"):
                entry["selector"] = str(step["selector"])
            if step.get("label"):
                entry["label"] = str(step["label"])

        if action == "fill":
            entry["value"] = str(step.get("value", "test@example.com"))

        if action == "wait":
            entry["ms"] = int(step.get("ms", 1000))
            entry["label"] = build_step_label(entry)

        if action == "open_page" and not entry.get("label"):
            entry["label"] = build_step_label(entry)

        if action == "capture" and not entry.get("label"):
            entry["label"] = build_step_label(entry)

        validated.append(_enrich_step_with_context(entry, index))

    validated = _finalize_plan(validated)

    if len(validated) < MIN_STEPS:
        raise ValueError(f"Plan must contain at least {MIN_STEPS} steps")

    if any(step.get("target") in GENERIC_TARGETS for step in validated):
        raise ValueError("Generic page/text targets are not allowed")

    if _is_generic_plan(validated, intent):
        raise ValueError("Plan is too generic")

    context_validated, rejections = validate_plan_against_context(validated, index)
    if rejections:
        logger.warning("[Planner] Context rejected %d step(s): %s", len(rejections), rejections)
    if len(context_validated) < MIN_STEPS:
        raise ValueError("Too few context-supported steps after validation")

    return _finalize_plan(context_validated), len(rejections)


def deterministic_fallback(goal: str, index: ContextIndex, intent: str) -> list[dict]:
    """Build a plan from discovered page elements only."""
    return build_context_plan(goal, intent, index)


async def generate_test_plan(
    url: str,
    goal: str,
    website_context: WebsiteContext | None = None,
) -> dict:
    planning_start = time.perf_counter()
    context = website_context or empty_context()
    index = ContextIndex(context)
    intent = detect_intent(goal)
    provider = get_ai_provider()
    source = "fallback"
    plan: list[dict] = []
    rejections = 0
    provider_name = provider.name

    logger.info("[Planner] Detected intent: %s", intent)
    logger.info("[Planner] Context summary: %s", index.summary())
    logger.info("[Planner] Using AI provider: %s", provider_name)

    if await provider.is_available():
        logger.info("[Planner] Provider '%s' available", provider_name)
        logger.info("[Planner] Generating context-aware plan with %s", settings.model_name)
        try:
            result = await provider.generate_plan(
                url=url,
                goal=goal,
                intent=intent,
                website_context=index.planner_snapshot(),
            )
            if result.success:
                data = _parse_json_response(result.text)
                plan, rejections = _validate_plan(data.get("plan", []), intent, index)
                source = result.provider or provider_name
            else:
                logger.warning("[Planner] Provider generation failed: %s", result.error)
        except Exception as exc:
            logger.warning("[Planner] Provider plan parsing failed: %s", exc)
    else:
        logger.warning("[Planner] Provider '%s' unavailable", provider_name)

    if not plan:
        logger.info("[Planner] Using context-aware fallback for intent=%s", intent)
        plan = deterministic_fallback(goal, index, intent)
        source = "fallback"

    planning_time_ms = int((time.perf_counter() - planning_start) * 1000)
    validation_score = compute_validation_score(
        plan_steps=len(plan),
        min_steps=MIN_STEPS,
        max_steps=MAX_STEPS,
        rejections=rejections,
    )
    metadata = build_plan_metadata(
        planner_source=source,
        planning_time_ms=planning_time_ms,
        validation_score=validation_score,
        provider=provider_name,
    )

    return {
        "plan": plan,
        "source": source,
        "intent": intent,
        "metadata": metadata,
    }
