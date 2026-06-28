"""Evidence model for Sprint 4 AI reasoning."""

from __future__ import annotations

from enum import Enum
from typing import TypedDict


class EvidenceSource(str, Enum):
    DOM = "DOM"
    SCREENSHOT = "Screenshot"
    ASSERTION = "Assertion"
    CONTEXT = "Context"
    TIMELINE = "Timeline"
    CONSOLE = "Console"
    NETWORK = "Network"


class Evidence(TypedDict, total=False):
    source: str
    description: str
    value: str
    confidence: float
