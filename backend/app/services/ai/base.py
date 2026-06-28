"""Base interface for AI planning providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class PlanGenerationResult:
    """Normalized response from any AI planning provider."""

    success: bool
    text: str = ""
    error: str = ""
    provider: str = ""
    latency_ms: int = 0


class BaseAIProvider(ABC):
    """Abstract AI provider used by the planner — never bind to a single vendor."""

    name: str = "base"

    @abstractmethod
    async def generate_plan(
        self,
        *,
        url: str,
        goal: str,
        intent: str,
        website_context: dict,
    ) -> PlanGenerationResult:
        """Generate a JSON test plan for the given URL, goal, and page context."""

    @abstractmethod
    async def is_available(self) -> bool:
        """Return True when the provider is configured and reachable."""
