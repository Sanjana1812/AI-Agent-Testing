"""Claude AI planning provider (placeholder — not integrated yet)."""

from __future__ import annotations

from app.services.ai.base import BaseAIProvider, PlanGenerationResult


class ClaudeProvider(BaseAIProvider):
    name = "claude"

    async def is_available(self) -> bool:
        return False

    async def generate_plan(
        self,
        *,
        url: str,
        goal: str,
        intent: str,
        website_context: dict,
    ) -> PlanGenerationResult:
        return PlanGenerationResult(
            success=False,
            error="Claude provider is not integrated yet",
            provider=self.name,
        )
