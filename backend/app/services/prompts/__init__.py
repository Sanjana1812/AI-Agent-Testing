"""Prompt registry package."""

from app.services.prompts.planner_v1 import PURPOSE as PLANNER_PURPOSE, VERSION as PLANNER_VERSION
from app.services.prompts.rca_v1 import PURPOSE as RCA_PURPOSE, VERSION as RCA_VERSION
from app.services.prompts.registry import PromptDefinition, get_prompt, list_prompts, load_registry
from app.services.prompts.summary_v1 import PURPOSE as SUMMARY_PURPOSE, VERSION as SUMMARY_VERSION

__all__ = [
    "PromptDefinition",
    "get_prompt",
    "list_prompts",
    "load_registry",
    "PLANNER_VERSION",
    "PLANNER_PURPOSE",
    "RCA_VERSION",
    "RCA_PURPOSE",
    "SUMMARY_VERSION",
    "SUMMARY_PURPOSE",
]
