"""Gemini AI planning provider (placeholder — not integrated yet)."""

from __future__ import annotations

import logging

from app.services.ai.base import BaseAIProvider, PlanGenerationResult

logger = logging.getLogger(__name__)


class GeminiProvider(BaseAIProvider):
    """Placeholder provider for future Gemini integration."""

    name = "gemini"

    async def is_available(self) -> bool:
        logger.debug("[GeminiProvider] Placeholder provider is not configured")
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
            error="Gemini provider is not integrated yet",
            provider=self.name,
        )
