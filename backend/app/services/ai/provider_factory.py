"""Factory for AI planning providers."""

from __future__ import annotations

import logging

from app.config import settings
from app.services.ai.base import BaseAIProvider
from app.services.ai.providers.claude_provider import ClaudeProvider
from app.services.ai.providers.gemini_provider import GeminiProvider
from app.services.ai.providers.ollama_provider import OllamaProvider
from app.services.ai.providers.openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)

_PROVIDERS: dict[str, type[BaseAIProvider]] = {
    "ollama": OllamaProvider,
    "gemini": GeminiProvider,
    "claude": ClaudeProvider,
    "openai": OpenAIProvider,
}


def get_ai_provider(provider_name: str | None = None) -> BaseAIProvider:
    """Resolve a provider by name, defaulting to configured settings."""
    name = (provider_name or settings.ai_provider).strip().lower()
    provider_cls = _PROVIDERS.get(name)
    if not provider_cls:
        logger.warning("[AIProvider] Unknown provider '%s', falling back to ollama", name)
        provider_cls = OllamaProvider
    return provider_cls()


def registered_providers() -> list[str]:
    return sorted(_PROVIDERS.keys())
