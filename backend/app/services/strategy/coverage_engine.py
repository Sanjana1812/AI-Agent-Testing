"""Coverage engine — estimate structural test coverage from plan vs site (Sprint 4.1A)."""

from __future__ import annotations

import re

from app.services.planner.context_index import ContextIndex
from app.services.strategy.models import COVERAGE_AREA_NAMES, CoverageArea, CoverageReport
from app.services.strategy.models import TestingStrategy
from app.services.website_context.json_builder import WebsiteContext

AREA_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Navigation": ("nav", "navigation", "menu", "click", "open_page"),
    "Hero": ("hero", "banner", "heading", "h1"),
    "Sections": ("section", "main", "content", "scroll"),
    "Buttons": ("button", "cta", "submit", "click"),
    "Forms": ("form", "fill", "email", "password", "verify_form"),
    "Footer": ("footer",),
    "Search": ("search",),
    "Authentication": ("login", "sign in", "sign up", "password", "auth"),
    "Checkout": ("checkout", "cart", "payment", "buy"),
    "Documentation": ("docs", "documentation", "api", "reference", "guide"),
}


def _normalize(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value).strip()).lower()


def _plan_blob(plan: list[dict]) -> str:
    parts: list[str] = []
    for step in plan:
        parts.append(_normalize(step.get("action")))
        parts.append(_normalize(step.get("target")))
        parts.append(_normalize(step.get("label")))
        parts.append(_normalize(step.get("text")))
    return " ".join(part for part in parts if part)


def _area_applicable(area: str, index: ContextIndex) -> tuple[bool, str]:
    if area == "Navigation":
        applicable = len(index.context.get("navigation", [])) > 0
        return applicable, f"{len(index.context.get('navigation', []))} nav links"
    if area == "Hero":
        applicable = index.has_hero() or bool(index.hero_heading())
        return applicable, "Hero or primary heading present" if applicable else "No hero detected"
    if area == "Sections":
        count = len(index.context.get("sections", []))
        return count > 0, f"{count} sections"
    if area == "Buttons":
        count = len(index.usable_buttons())
        return count > 0, f"{count} buttons"
    if area == "Forms":
        count = len(index.context.get("forms", []))
        return count > 0, f"{count} forms"
    if area == "Footer":
        applicable = bool(index.context.get("footer")) or any(
            section.get("semantic_type") == "footer" for section in index.context.get("sections", [])
        )
        return applicable, "Footer links/section present" if applicable else "No footer detected"
    if area == "Search":
        blob = " ".join(
            _normalize(item.get("text"))
            for item in index.context.get("buttons", []) + index.context.get("navigation", [])
        )
        applicable = "search" in blob
        return applicable, "Search control detected" if applicable else "No search control"
    if area == "Authentication":
        applicable = index.has_password_field() or any(
            "login" in _normalize(form.get("classification")) for form in index.context.get("forms", [])
        )
        return applicable, "Authentication surface detected" if applicable else "No auth forms"
    if area == "Checkout":
        blob = " ".join(_normalize(button.get("text")) for button in index.usable_buttons())
        applicable = any(token in blob for token in ("cart", "checkout", "buy", "shop"))
        return applicable, "Commerce actions detected" if applicable else "No checkout signals"
    if area == "Documentation":
        blob = " ".join(
            _normalize(link.get("text"))
            for link in index.context.get("navigation", []) + index.context.get("links", [])
        )
        applicable = any(token in blob for token in ("doc", "api", "guide", "reference"))
        return applicable, "Documentation links detected" if applicable else "No documentation links"
    return False, "Unknown area"


def _area_tested(area: str, plan_blob: str) -> tuple[bool, str]:
    keywords = AREA_KEYWORDS.get(area, ())
    if any(keyword in plan_blob for keyword in keywords):
        return True, "Covered by planned steps"
    return False, "Not represented in current plan"


def estimate_coverage(
    context: WebsiteContext,
    plan: list[dict],
    strategy: TestingStrategy | None = None,
) -> CoverageReport:
    """Estimate tested vs applicable structural coverage for the current plan."""
    index = ContextIndex(context)
    plan_blob = _plan_blob(plan)
    areas: list[CoverageArea] = []

    for area in COVERAGE_AREA_NAMES:
        applicable, applicability_reason = _area_applicable(area, index)
        if not applicable:
            areas.append(CoverageArea(area=area, status="not_applicable", reason=applicability_reason))
            continue

        tested, test_reason = _area_tested(area, plan_blob)
        status = "tested" if tested else "not_tested"
        areas.append(CoverageArea(area=area, status=status, reason=test_reason))

    applicable_areas = [area for area in areas if area.status != "not_applicable"]
    tested_count = sum(1 for area in applicable_areas if area.status == "tested")
    applicable_count = len(applicable_areas)
    percent = (tested_count / applicable_count * 100.0) if applicable_count else 0.0

    return CoverageReport(
        areas=areas,
        estimated_coverage_percent=percent,
        tested_count=tested_count,
        applicable_count=applicable_count,
    )
