"""Explainability engine — confidence breakdown for WebsiteAnalysis (Sprint 4.1A)."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from app.services.planner.context_index import ContextIndex
from app.services.strategy.models import ConfidenceBreakdown, SignalContribution
from app.services.website_analysis.classifier import classify_website_type
from app.services.website_analysis.models import WebsiteAnalysis
from app.services.website_context.context_utils import is_context_empty
from app.services.website_context.json_builder import WebsiteContext

SIGNAL_WEIGHTS: dict[str, float] = {
    "Navigation": 0.18,
    "Hero": 0.12,
    "Buttons": 0.10,
    "Forms": 0.12,
    "Metadata": 0.15,
    "Headings": 0.10,
    "Internal Links": 0.13,
    "URL Structure": 0.10,
}


def _clamp(value: float, *, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _score_navigation(index: ContextIndex) -> tuple[float, str]:
    count = len(index.context.get("navigation", []))
    if count >= 6:
        return 1.0, f"{count} navigation links detected"
    if count >= 3:
        return 0.75, f"{count} navigation links detected"
    if count >= 1:
        return 0.45, f"{count} navigation link(s) detected"
    return 0.0, "No navigation links extracted"


def _score_hero(index: ContextIndex) -> tuple[float, str]:
    if index.has_hero():
        heading = (index.hero_heading() or {}).get("text", "")
        return 1.0, f"Hero section detected{f' ({heading})' if heading else ''}"
    heading = index.hero_heading()
    if heading and heading.get("text"):
        return 0.7, f"Primary heading detected: {heading['text']}"
    return 0.0, "No hero section or primary heading found"


def _score_buttons(index: ContextIndex) -> tuple[float, str]:
    count = len(index.usable_buttons())
    if count >= 4:
        return 1.0, f"{count} interactive buttons detected"
    if count >= 1:
        return 0.6, f"{count} interactive button(s) detected"
    return 0.0, "No interactive buttons found"


def _score_forms(index: ContextIndex) -> tuple[float, str]:
    forms = index.context.get("forms", [])
    if not forms:
        return 0.0, "No forms detected"
    classifications = [str(form.get("classification", "form")) for form in forms[:3]]
    return min(1.0, 0.5 + len(forms) * 0.15), f"{len(forms)} form(s): {', '.join(classifications)}"


def _score_metadata(context: WebsiteContext) -> tuple[float, str]:
    metadata = context.get("metadata", {})
    title = str(metadata.get("title", "")).strip()
    description = str(metadata.get("meta_description", "")).strip()
    score = 0.0
    parts: list[str] = []
    if title:
        score += 0.55
        parts.append(f"title '{title[:48]}'")
    if description:
        score += 0.45
        parts.append("meta description present")
    if not parts:
        return 0.0, "Page metadata missing"
    return _clamp(score), "; ".join(parts)


def _score_headings(index: ContextIndex) -> tuple[float, str]:
    headings = index.context.get("headings", [])
    if len(headings) >= 4:
        return 1.0, f"{len(headings)} headings extracted"
    if len(headings) >= 1:
        return 0.55, f"{len(headings)} heading(s) extracted"
    return 0.0, "No headings extracted"


def _score_internal_links(index: ContextIndex) -> tuple[float, str]:
    links = index.context.get("links", [])
    internal = [
        link
        for link in links
        if str(link.get("href", "")).startswith(("/", "#")) or link.get("internal")
    ]
    count = len(internal) or len(links)
    if count >= 10:
        return 1.0, f"{count} internal links discovered"
    if count >= 3:
        return 0.7, f"{count} internal links discovered"
    if count >= 1:
        return 0.4, f"{count} internal link(s) discovered"
    return 0.0, "No internal links discovered"


def _score_url_structure(context: WebsiteContext) -> tuple[float, str]:
    url = str(context.get("metadata", {}).get("current_url", "")).strip()
    if not url:
        return 0.0, "URL not available"
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    segments = [segment for segment in path.split("/") if segment]
    depth = len(segments)
    if depth >= 2:
        return 0.85, f"Structured path '/{'/'.join(segments[:3])}'"
    if depth == 1:
        return 0.65, f"Single-segment path '/{segments[0]}'"
    if parsed.netloc:
        return 0.5, f"Root domain path for {parsed.netloc}"
    return 0.2, "Minimal URL structure"


def build_confidence_breakdown(
    context: WebsiteContext,
    analysis: WebsiteAnalysis,
) -> ConfidenceBreakdown:
    """Produce weighted signal contributions explaining the classification."""
    index = ContextIndex(context)
    scorers = {
        "Navigation": lambda: _score_navigation(index),
        "Hero": lambda: _score_hero(index),
        "Buttons": lambda: _score_buttons(index),
        "Forms": lambda: _score_forms(index),
        "Metadata": lambda: _score_metadata(context),
        "Headings": lambda: _score_headings(index),
        "Internal Links": lambda: _score_internal_links(index),
        "URL Structure": lambda: _score_url_structure(context),
    }

    signals: list[SignalContribution] = []
    weighted_total = 0.0
    weight_sum = 0.0

    for name, weight in SIGNAL_WEIGHTS.items():
        score, evidence = scorers[name]()
        contribution = score * weight
        weighted_total += contribution
        weight_sum += weight
        signals.append(
            SignalContribution(
                signal=name,
                weight=weight,
                score=score,
                contribution=contribution,
                evidence=evidence,
            )
        )

    if is_context_empty(context) or analysis.confidence <= 0:
        return ConfidenceBreakdown(
            signals=signals,
            total_confidence=0.0,
            reasoning=(
                "Website context was not extracted — confidence signals are unavailable. "
                "Restore Playwright context extraction before relying on classification scores."
            ),
        )

    signal_confidence = weighted_total / weight_sum if weight_sum else 0.0
    total_confidence = analysis.confidence if analysis.confidence > 0 else signal_confidence

    top = sorted(signals, key=lambda item: item.contribution, reverse=True)[:3]
    top_labels = ", ".join(f"{item.signal} ({item.contribution * 100:.0f}%)" for item in top)
    _, _, classifier_reasoning = classify_website_type(context)
    reasoning = (
        f"Classified as {analysis.website_type} with {total_confidence * 100:.0f}% confidence. "
        f"Strongest signals: {top_labels}. {analysis.reasoning or classifier_reasoning}"
    )
    reasoning = re.sub(r"\s+", " ", reasoning).strip()

    return ConfidenceBreakdown(
        signals=signals,
        total_confidence=total_confidence,
        reasoning=reasoning,
    )
