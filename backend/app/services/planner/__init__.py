"""Context-aware AI planner utilities."""

from app.services.planner.context_cache import ContextCache, contexts_from_cache
from app.services.planner.semantic_filter import filter_context, is_decorative_element, is_ignored_label
from app.services.planner.context_fallback import build_context_plan
from app.services.planner.context_index import ContextIndex
from app.services.planner.context_refresh import cache_stats_dict, refresh_for_url
from app.services.planner.context_validator import validate_plan_against_context
from app.services.planner.dom_fingerprint import fingerprint_from_context, significantly_changed
from app.services.planner.intent_classifier import IntentType, classify_intent, detect_intent
from app.services.planner.journey_builder import build_validated_journey
from app.services.planner.journey_validator import validate_journey
from app.services.planner.multi_page_journey import resolve_plan_for_contexts, try_build_adaptive_journey
from app.services.planner.navigation_graph import NavigationGraph
from app.services.planner.page_observer import PageObserver, PageSnapshot
from app.services.planner.selector_resolver import resolve_plan_selectors

__all__ = [
    "ContextCache",
    "ContextIndex",
    "NavigationGraph",
    "IntentType",
    "PageObserver",
    "PageSnapshot",
    "classify_intent",
    "detect_intent",
    "build_context_plan",
    "build_validated_journey",
    "validate_plan_against_context",
    "validate_journey",
    "resolve_plan_selectors",
    "resolve_plan_for_contexts",
    "try_build_adaptive_journey",
    "contexts_from_cache",
    "cache_stats_dict",
    "refresh_for_url",
    "fingerprint_from_context",
    "significantly_changed",
    "is_ignored_label",
    "is_decorative_element",
    "filter_context",
]
