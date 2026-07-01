"""Sprint 3.8 verification harness for dynamic context refresh."""

from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

BASE_URL = "https://demo.test"


def section(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def _nav(text: str, href: str) -> dict:
    return {
        "text": text,
        "href": href,
        "selector": f'a[href="{href}"]',
        "internal": True,
        "priority": 90,
        "visible": True,
        "classification": "Primary Navigation",
    }


def homepage_context() -> dict:
    return {
        "metadata": {"title": "Demo Home", "current_url": BASE_URL},
        "navigation": [_nav("Services", "/services"), _nav("Contact", "/contact")],
        "headings": [{"level": 1, "text": "Welcome Home"}],
        "buttons": [
            {
                "text": "Services",
                "href": "/services",
                "selector": 'a[href="/services"]',
                "priority": 95,
                "classification": "CTA",
                "type": "cta",
                "visible": True,
                "enabled": True,
                "tag": "a",
            },
            {
                "text": "Contact",
                "href": "/contact",
                "selector": 'a[href="/contact"]',
                "priority": 90,
                "classification": "CTA",
                "type": "cta",
                "visible": True,
                "enabled": True,
                "tag": "a",
            },
        ],
        "sections": [{"heading": "Features", "semantic_type": "features", "priority": 70, "id": "features", "tag": "section"}],
        "footer": [{"text": "Footer", "selector": "footer", "visible": True}],
        "links": [],
        "forms": [],
    }


def services_context() -> dict:
    return {
        "metadata": {"title": "Services", "current_url": f"{BASE_URL}/services"},
        "navigation": [_nav("Home", "/"), _nav("Contact", "/contact")],
        "headings": [{"level": 1, "text": "Our Services"}],
        "buttons": [
            {
                "text": "Contact",
                "href": "/contact",
                "selector": 'a[href="/contact"]',
                "priority": 90,
                "classification": "CTA",
                "type": "cta",
                "visible": True,
                "enabled": True,
                "tag": "a",
            }
        ],
        "sections": [{"heading": "Service Plans", "semantic_type": "features", "priority": 80, "id": "plans", "tag": "section"}],
        "footer": [{"text": "Footer", "selector": "footer", "visible": True}],
        "links": [],
        "forms": [],
    }


def contact_context() -> dict:
    return {
        "metadata": {"title": "Contact", "current_url": f"{BASE_URL}/contact"},
        "navigation": [_nav("Home", "/"), _nav("Services", "/services")],
        "headings": [{"level": 1, "text": "Contact Us"}],
        "buttons": [],
        "sections": [],
        "footer": [{"text": "Footer", "selector": "footer", "visible": True}],
        "links": [],
        "forms": [
            {
                "classification": "contact",
                "selector": "form#contact",
                "fields": [{"name": "email", "type": "email"}],
                "visible": True,
            }
        ],
    }


def mock_loader(url: str) -> dict:
    path = urlparse(url).path.rstrip("/") or "/"
    if path == "/services":
        return services_context()
    if path == "/contact":
        return contact_context()
    return homepage_context()


def audit_modules() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    for module in (
        "app.services.planner.dom_fingerprint",
        "app.services.planner.context_cache",
        "app.services.planner.page_observer",
        "app.services.planner.context_refresh",
        "app.services.planner.multi_page_journey",
    ):
        try:
            __import__(module)
            findings["passed"].append(f"Import OK: {module}")
        except Exception as exc:
            findings["failed"].append(f"Import failed {module}: {exc}")
    return findings


def audit_page_observer() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.planner.page_observer import PageObserver

    observer = PageObserver()
    before = observer.from_context(homepage_context(), BASE_URL)
    after_scroll = observer.from_context(homepage_context(), BASE_URL)
    if not observer.should_refresh({"action": "scroll"}, before=before, after=after_scroll):
        findings["passed"].append("Scroll does not trigger refresh")
    else:
        findings["failed"].append("Scroll incorrectly triggers refresh")

    after_nav = observer.from_context(services_context(), f"{BASE_URL}/services")
    if observer.should_refresh({"action": "click", "target": "link"}, before=before, after=after_nav):
        findings["passed"].append("Navigation triggers refresh")
    else:
        findings["failed"].append("Navigation should trigger refresh")
    return findings


def audit_dom_fingerprint() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.planner.dom_fingerprint import fingerprint_from_context, significantly_changed

    home_fp = fingerprint_from_context(homepage_context())
    services_fp = fingerprint_from_context(services_context())
    if significantly_changed(home_fp, services_fp):
        findings["passed"].append("Services page fingerprint differs from homepage")
    else:
        findings["failed"].append("Fingerprint should detect page change")

    same_fp = fingerprint_from_context(homepage_context())
    if not significantly_changed(home_fp, same_fp):
        findings["passed"].append("Stable fingerprint for unchanged page")
    else:
        findings["failed"].append("Unchanged page should not change fingerprint significantly")
    return findings


def audit_context_cache() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.planner.context_cache import ContextCache, normalize_url

    cache = ContextCache()
    home_key = normalize_url(BASE_URL)
    cache.get_or_load(home_key, mock_loader)
    cache.get_or_load(home_key, mock_loader)
    if cache.stats.cache_hits >= 1 and cache.stats.cache_misses == 1:
        findings["passed"].append("Cache reuses context on revisit")
    else:
        findings["failed"].append(
            f"Expected 1 miss and 1 hit, got misses={cache.stats.cache_misses} hits={cache.stats.cache_hits}"
        )

    services_key = normalize_url(f"{BASE_URL}/services")
    cache.get_or_load(services_key, mock_loader)
    cache.get_or_load(home_key, mock_loader)
    if cache.stats.cache_hits >= 2:
        findings["passed"].append("Back navigation reuses cached homepage context")
    else:
        findings["failed"].append("Homepage cache should be reused after visiting another page")
    return findings


def audit_multi_page_journey() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.planner.context_cache import ContextCache, normalize_url
    from app.services.planner.context_index import ContextIndex
    from app.services.planner.intent_classifier import IntentType
    from app.services.planner.journey_builder import build_validated_journey
    from app.services.planner.plan_metadata import PLANNER_VERSION

    cache = ContextCache()
    home = homepage_context()
    index = ContextIndex(home)
    plan = build_validated_journey(
        "check the flow",
        IntentType.FLOW,
        index,
        base_url=BASE_URL,
        cache=cache,
        loader=mock_loader,
    )

    if not plan:
        findings["failed"].append("Adaptive multi-page plan was not generated")
        return findings

    findings["passed"].append(f"Multi-page plan generated with {len(plan)} steps")

    click_idx = next((i for i, step in enumerate(plan) if step.get("action") == "click"), None)
    if click_idx is None:
        findings["failed"].append("Plan missing navigation click")
        return findings

    post_click = plan[click_idx + 1 :]
    refreshed = [step for step in post_click if step.get("context_refresh")]
    if refreshed:
        findings["passed"].append("Context refresh metadata present after navigation")
    else:
        findings["failed"].append("Expected context_refresh steps after navigation")

    homepage_key = normalize_url(BASE_URL)
    services_key = normalize_url(f"{BASE_URL}/services")
    stale_hero = [
        step
        for step in post_click
        if step.get("target") == "hero"
        and step.get("context_url") == services_key
        and "welcome home" in (step.get("label") or "").lower()
    ]
    if not stale_hero:
        findings["passed"].append("No homepage hero verification after navigating away")
    else:
        findings["failed"].append("Stale homepage hero verification detected on services page")

    services_hero = [
        step
        for step in plan
        if step.get("target") == "hero" and step.get("context_url") == services_key
    ]
    if services_hero:
        findings["passed"].append("Services page hero verification uses refreshed context")
    else:
        findings["warnings"].append("Services hero verification not found")

    if cache.stats.context_refreshes >= 1:
        findings["passed"].append("Context refresh counter incremented")
    else:
        findings["failed"].append("Expected at least one context refresh")

    if len(cache.stats.pages_visited) >= 2:
        findings["passed"].append("Multiple pages tracked in pages_visited")
    else:
        findings["failed"].append("Expected multiple pages in pages_visited")

    if PLANNER_VERSION == "3.9.1":
        findings["passed"].append("Planner version bumped to 3.9.1")
    else:
        findings["failed"].append(f"Expected planner version 3.9.1, got {PLANNER_VERSION}")
    return findings


def audit_metadata_schema() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.schemas import PlannerMetadata, PlanStep, RunTestResponse
    from app.services.planner.plan_metadata import build_plan_metadata

    metadata_fields = set(PlannerMetadata.model_fields.keys())
    for field in ("context_refreshes", "pages_visited", "cache_hits", "cache_misses"):
        if field in metadata_fields:
            findings["passed"].append(f"PlannerMetadata includes {field}")
        else:
            findings["failed"].append(f"PlannerMetadata missing {field}")

    step_fields = set(PlanStep.model_fields.keys())
    if "context_url" in step_fields:
        findings["passed"].append("Optional context_url on PlanStep")
    else:
        findings["failed"].append("PlanStep missing optional context_url")

    payload = build_plan_metadata(
        planner_source="fallback",
        planning_time_ms=10,
        validation_score=90.0,
        context_refreshes=2,
        pages_visited=["https://demo.test", "https://demo.test/services"],
        cache_hits=1,
        cache_misses=2,
    )
    if payload.get("planner_version") == "3.9.1" and payload.get("context_refreshes") == 2:
        findings["passed"].append("build_plan_metadata reports refresh statistics")
    else:
        findings["failed"].append("build_plan_metadata missing refresh statistics")

    required = {"id", "goal", "status", "ai_plan", "ai_plan_source", "steps", "failures", "summary"}
    if required.issubset(set(RunTestResponse.model_fields.keys())):
        findings["passed"].append("RunTestResponse core schema unchanged")
    else:
        findings["failed"].append("RunTestResponse core fields changed")
    return findings


def audit_backward_compat() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.playwright_runner import _execute_sync

    source = inspect.getsource(_execute_sync)
    blocked = ("context_refresh", "ContextCache", "PageObserver", "dom_fingerprint")
    if not any(token in source for token in blocked):
        findings["passed"].append("Playwright _execute_sync unchanged")
    else:
        findings["failed"].append("Playwright execution engine references context refresh modules")
    return findings


def main() -> None:
    all_findings = {}

    section("1. MODULE IMPORTS")
    all_findings["modules"] = audit_modules()
    print(json.dumps(all_findings["modules"], indent=2))

    section("2. PAGE OBSERVER")
    all_findings["observer"] = audit_page_observer()
    print(json.dumps(all_findings["observer"], indent=2))

    section("3. DOM FINGERPRINT")
    all_findings["fingerprint"] = audit_dom_fingerprint()
    print(json.dumps(all_findings["fingerprint"], indent=2))

    section("4. CONTEXT CACHE")
    all_findings["cache"] = audit_context_cache()
    print(json.dumps(all_findings["cache"], indent=2))

    section("5. MULTI-PAGE JOURNEY")
    all_findings["journey"] = audit_multi_page_journey()
    print(json.dumps(all_findings["journey"], indent=2))

    section("6. METADATA & SCHEMA")
    all_findings["metadata"] = audit_metadata_schema()
    print(json.dumps(all_findings["metadata"], indent=2))

    section("7. BACKWARD COMPATIBILITY")
    all_findings["compat"] = audit_backward_compat()
    print(json.dumps(all_findings["compat"], indent=2))

    failed = sum(len(v.get("failed", [])) for v in all_findings.values())
    print(f"\n{'=' * 60}\nTOTAL FAILURES: {failed}\n{'=' * 60}")


if __name__ == "__main__":
    main()
