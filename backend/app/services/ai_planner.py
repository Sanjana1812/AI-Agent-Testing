from __future__ import annotations

import json
import logging
import re
import time

from app.config import settings
from app.services.ai.provider_factory import get_ai_provider
from app.services.planner.context_cache import ContextCache, contexts_from_cache, normalize_url
from app.services.planner.context_index import ContextIndex
from app.services.planner.context_validator import validate_plan_against_context
from app.services.planner.display_labels import build_step_label
from app.services.planner.intent_classifier import (
    IntentType,
    classify_intent,
    detect_intent,
    legacy_intent_string,
)
from app.services.planner.journey_builder import build_validated_journey
from app.services.planner.journey_validator import validate_journey
from app.services.planner.navigation_graph import NavigationGraph
from app.services.planner.multi_page_journey import resolve_plan_for_contexts
from app.services.planner.plan_presentation import (
    build_journey_summary,
    build_planner_reasoning,
    is_minimal_fallback_plan,
    normalize_planner_source,
    polish_plan_labels,
    compute_planner_confidence,
)
from app.services.planner.plan_metadata import build_plan_metadata, compute_validation_score
from app.services.planner.selector_resolver import resolve_plan_selectors
from app.services.website_context import ContextService
from app.services.website_context.context_service import pool_context_loader
from app.services.website_context.json_builder import WebsiteContext, empty_context
from app.services.website_analysis import WebsiteAnalysis, analyze_website
from app.services.website_analysis.journey_builder import try_build_analysis_journey

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
    {"flow", "navigation", "login", "signup", "contact", "form", "search", "checkout", "dashboard", "profile", "general", "purchase"}
)

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


def deterministic_fallback(goal: str, index: ContextIndex, intent: IntentType | str) -> list[dict]:
    """Build an intent-aware journey from discovered page elements."""
    if isinstance(intent, str):
        resolved = classify_intent(goal)
    else:
        resolved = intent
    return build_validated_journey(goal, resolved, index)


async def generate_test_plan(
    url: str,
    goal: str,
    website_context: WebsiteContext | None = None,
    website_analysis: WebsiteAnalysis | None = None,
) -> dict:
    planning_start = time.perf_counter()
    context = website_context or empty_context()
    analysis = website_analysis or analyze_website(context, goal=goal)
    index = ContextIndex(context)
    intent_type = classify_intent(goal)
    intent = legacy_intent_string(intent_type)
    graph = NavigationGraph.from_context(index)
    provider = get_ai_provider()
    source = "fallback"
    plan: list[dict] = []
    rejections = 0
    provider_name = provider.name

    logger.info("[Planner] Detected intent: %s (%s)", intent, intent_type.value)
    logger.info("[Planner] Website analysis: %s (confidence=%.2f)", analysis.website_type, analysis.confidence)
    logger.info("[Planner] Context summary: %s", index.summary())
    logger.info("[Planner] Navigation graph: %s", graph.tree_summary())
    logger.info("[Planner] Using AI provider: %s", provider_name)

    planner_snapshot = index.planner_snapshot()
    planner_snapshot["website_analysis"] = analysis.to_dict()

    if await provider.is_available():
        logger.info("[Planner] Provider '%s' available", provider_name)
        logger.info("[Planner] Generating context-aware plan with %s", settings.model_name)
        try:
            result = await provider.generate_plan(
                url=url,
                goal=goal,
                intent=intent,
                website_context=planner_snapshot,
            )
            if result.success:
                data = _parse_json_response(result.text)
                candidate, rejections = _validate_plan(data.get("plan", []), intent, index)
                journey_ok, journey_reasons = validate_journey(candidate, intent_type, index)
                if journey_ok:
                    plan = candidate
                    source = result.provider or provider_name
                else:
                    logger.warning("[Planner] AI plan failed journey validation: %s", journey_reasons)
            else:
                logger.warning("[Planner] Provider generation failed: %s", result.error)
        except Exception as exc:
            logger.warning("[Planner] Provider plan parsing failed: %s", exc)
    else:
        logger.warning("[Planner] Provider '%s' unavailable", provider_name)

    if not plan and analysis.confidence >= 0.5:
        analysis_plan = try_build_analysis_journey(analysis, context, intent=intent_type)
        if analysis_plan:
            plan = analysis_plan
            source = "semantic_planner"

    if not plan:
        logger.info("[Planner] Using journey builder for intent=%s", intent_type.value)
        context_cache = ContextCache()
        context_cache.put(normalize_url(url), context)
        loader = pool_context_loader
        plan = build_validated_journey(
            goal,
            intent_type,
            index,
            base_url=url,
            cache=context_cache,
            loader=loader,
        )
        source = "semantic_planner"
    else:
        context_cache = ContextCache()
        context_cache.put(normalize_url(url), context)

    if any(step.get("context_url") for step in plan):
        contexts_by_url = contexts_from_cache(context_cache, context)
        contexts_by_url.setdefault(normalize_url(url), index)
        plan = resolve_plan_for_contexts(plan, contexts_by_url, index)
    else:
        plan = resolve_plan_selectors(plan, index)

    plan = polish_plan_labels(plan, base_url=url)

    if normalize_planner_source(source) == "semantic_planner" and is_minimal_fallback_plan(plan):
        source = "fallback"

    planning_time_ms = int((time.perf_counter() - planning_start) * 1000)
    validation_score = compute_validation_score(
        plan_steps=len(plan),
        min_steps=MIN_STEPS,
        max_steps=MAX_STEPS,
        rejections=rejections,
    )
    planner_confidence, confidence_label = compute_planner_confidence(plan, validation_score=validation_score)
    strategy = "AI Provider Plan" if normalize_planner_source(source) not in {"fallback", "semantic_planner"} else (
        "Analysis-Aware Journey" if analysis.confidence >= 0.5 and source == "semantic_planner"
        else "Semantic Journey Builder" if source != "fallback"
        else "Minimal Fallback Planner"
    )
    reasoning = build_planner_reasoning(
        context=context,
        intent=intent,
        plan=plan,
        base_url=url,
        planner_strategy=strategy,
    )
    journey_summary = build_journey_summary(plan, base_url=url)
    metadata = build_plan_metadata(
        planner_source=source,
        planning_time_ms=planning_time_ms,
        validation_score=validation_score,
        provider=provider_name,
        context_refreshes=context_cache.stats.context_refreshes,
        pages_visited=list(context_cache.stats.pages_visited),
        cache_hits=context_cache.stats.cache_hits,
        cache_misses=context_cache.stats.cache_misses,
        planner_confidence=planner_confidence,
        planner_confidence_label=confidence_label,
        detected_website_type=analysis.website_type or reasoning["detected_website_type"],
        detected_intent=reasoning["detected_intent"],
        primary_navigation=reasoning["primary_navigation"],
        planner_strategy=reasoning["planner_strategy"],
        generated_journey=journey_summary,
        website_type=analysis.website_type,
        business_domain=analysis.business_domain,
        primary_goal=analysis.primary_goal,
        target_audience=analysis.target_audience,
        recommended_test_flow=analysis.recommended_test_flow,
        high_risk_areas=analysis.high_risk_areas,
        testing_priority=analysis.testing_priority,
        analysis_confidence=analysis.confidence,
        analysis_reasoning=analysis.reasoning,
        testing_strategy=f"Prioritize {', '.join(analysis.testing_priority[:3])}",
    )

    return {
        "plan": plan,
        "source": source,
        "intent": intent,
        "metadata": metadata,
        "website_analysis": analysis.to_dict(),
    }
