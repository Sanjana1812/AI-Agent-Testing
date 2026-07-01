"""Verify AI provider abstraction is ready for planning and future RCA."""

from __future__ import annotations

import inspect

from app.services.ai.base import BaseAIProvider, PlanGenerationResult
from app.services.ai.provider_factory import get_ai_provider, registered_providers

REQUIRED_PROVIDERS = ("ollama", "gemini", "claude", "openai")


def verify_provider_instance(provider: BaseAIProvider) -> list[str]:
    """Return validation errors for a single provider instance."""
    errors: list[str] = []

    if not isinstance(provider, BaseAIProvider):
        errors.append(f"{provider!r} is not a BaseAIProvider")
        return errors

    if not provider.name:
        errors.append("Provider missing name")

    for method_name in ("generate_plan", "is_available"):
        method = getattr(provider, method_name, None)
        if method is None or not callable(method):
            errors.append(f"Provider '{provider.name}' missing {method_name}()")
        elif not inspect.iscoroutinefunction(method):
            errors.append(f"Provider '{provider.name}.{method_name}' must be async")

    generate_plan_sig = inspect.signature(provider.generate_plan)
    required_params = {"url", "goal", "intent", "website_context"}
    if not required_params.issubset(generate_plan_sig.parameters):
        missing = required_params - set(generate_plan_sig.parameters)
        errors.append(f"Provider '{provider.name}.generate_plan' missing params: {missing}")

    return errors


def verify_provider_abstraction() -> list[str]:
    """Verify all registered providers implement the shared abstraction."""
    errors: list[str] = []

    registered = set(registered_providers())
    for name in REQUIRED_PROVIDERS:
        if name not in registered:
            errors.append(f"Provider '{name}' not registered")

    for name in REQUIRED_PROVIDERS:
        provider = get_ai_provider(name)
        errors.extend(verify_provider_instance(provider))

    return errors


def verify_plan_generation_result_shape() -> list[str]:
    """Verify PlanGenerationResult exposes the normalized contract."""
    errors: list[str] = []
    result = PlanGenerationResult(success=True, text="{}", provider="test", latency_ms=1)
    for field in ("success", "text", "error", "provider", "latency_ms"):
        if not hasattr(result, field):
            errors.append(f"PlanGenerationResult missing field: {field}")
    return errors
