"""Confidence scoring for selector candidates."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SelectorType(str, Enum):
    DATA_TESTID = "data-testid"
    ID = "id"
    HREF = "href"
    ARIA_LABEL = "aria-label"
    TEXT = "text"
    NAME = "name"
    PLACEHOLDER = "placeholder"
    CSS = "css"
    ROLE = "role"
    XPATH = "xpath"
    TAG = "tag"


CONFIDENCE_BY_TYPE: dict[SelectorType, int] = {
    SelectorType.DATA_TESTID: 100,
    SelectorType.ID: 95,
    SelectorType.HREF: 90,
    SelectorType.ARIA_LABEL: 85,
    SelectorType.TEXT: 80,
    SelectorType.NAME: 75,
    SelectorType.PLACEHOLDER: 70,
    SelectorType.CSS: 65,
    SelectorType.ROLE: 40,
    SelectorType.XPATH: 35,
    SelectorType.TAG: 20,
}

MIN_CONFIDENCE_THRESHOLD = 55


@dataclass(frozen=True)
class RankedSelector:
    selector: str
    selector_type: SelectorType
    confidence: int
    strategy: str = "ranked"


def rank_selectors(candidates: list[RankedSelector]) -> list[RankedSelector]:
    """Return candidates sorted by confidence (highest first)."""
    return sorted(candidates, key=lambda item: item.confidence, reverse=True)


def best_selector(candidates: list[RankedSelector]) -> RankedSelector | None:
    ranked = rank_selectors(candidates)
    return ranked[0] if ranked else None


def meets_confidence_threshold(candidate: RankedSelector, *, threshold: int = MIN_CONFIDENCE_THRESHOLD) -> bool:
    return candidate.confidence >= threshold
