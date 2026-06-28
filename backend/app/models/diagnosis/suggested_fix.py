"""Suggested fix model for Sprint 4 AI reasoning."""

from __future__ import annotations

from enum import Enum
from typing import TypedDict


class SuggestedFixType(str, Enum):
    SELECTOR = "Selector"
    TIMING = "Timing"
    WAIT_STRATEGY = "Wait Strategy"
    PLANNER = "Planner"
    ACCESSIBILITY = "Accessibility"
    NETWORK = "Network"
    RESPONSIVE = "Responsive"


class SuggestedFix(TypedDict, total=False):
    type: str
    title: str
    description: str
    priority: str
    example: str
