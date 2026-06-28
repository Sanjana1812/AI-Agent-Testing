"""Backward-compatible Ollama client — delegates to the AI provider layer."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.ai.provider_factory import get_ai_provider


@dataclass
class PlanGenerationResult:
    success: bool
    text: str = ""
    error: str = ""


async def generate_plan(
    url: str,
    goal: str,
    intent: str = "general",
    website_context: dict | None = None,
) -> PlanGenerationResult:
    provider = get_ai_provider("ollama")
    result = await provider.generate_plan(
        url=url,
        goal=goal,
        intent=intent,
        website_context=website_context or {},
    )
    return PlanGenerationResult(success=result.success, text=result.text, error=result.error)
