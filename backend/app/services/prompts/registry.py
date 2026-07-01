"""Prompt template registry for AI services (Sprint 4.0)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.services.prompts import planner_v1, rca_v1, summary_v1


@dataclass(frozen=True)
class PromptDefinition:
    """Registered prompt with version metadata."""

    key: str
    version: str
    purpose: str
    template: str
    render: Callable[..., str] | None = None


_REGISTRY: dict[str, PromptDefinition] = {}


def _register(defn: PromptDefinition) -> PromptDefinition:
    _REGISTRY[defn.key] = defn
    return defn


planner_prompt = _register(
    PromptDefinition(
        key="planner_v1",
        version=planner_v1.VERSION,
        purpose=planner_v1.PURPOSE,
        template=planner_v1.TEMPLATE,
        render=planner_v1.render,
    )
)

rca_prompt = _register(
    PromptDefinition(
        key="rca_v1",
        version=rca_v1.VERSION,
        purpose=rca_v1.PURPOSE,
        template=rca_v1.TEMPLATE,
        render=rca_v1.render,
    )
)

summary_prompt = _register(
    PromptDefinition(
        key="summary_v1",
        version=summary_v1.VERSION,
        purpose=summary_v1.PURPOSE,
        template=summary_v1.TEMPLATE,
        render=summary_v1.render,
    )
)


def get_prompt(key: str) -> PromptDefinition:
    """Resolve a prompt definition by registry key."""
    if key not in _REGISTRY:
        raise KeyError(f"Unknown prompt key: {key}")
    return _REGISTRY[key]


def list_prompts() -> list[str]:
    """Return all registered prompt keys."""
    return sorted(_REGISTRY.keys())


def load_registry() -> dict[str, PromptDefinition]:
    """Return a copy of the full prompt registry."""
    return dict(_REGISTRY)
