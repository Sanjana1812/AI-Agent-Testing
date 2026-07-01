"""Shared planning prompt builder for AI providers."""

from __future__ import annotations

from app.services.prompts.planner_v1 import render


def build_planning_prompt(url: str, goal: str, intent: str, website_context: dict) -> str:
    return render(url=url, goal=goal, intent=intent, website_context=website_context)
