"""Goal completion evaluation — compares goal, planner output, and executed steps."""

from __future__ import annotations

import re
from typing import Any

from app.services.evaluation.explainability import DimensionEvaluation

_THEME_ALIASES: dict[str, str] = {
    "nav": "navigation",
    "navigation": "navigation",
    "menu": "navigation",
    "header": "navigation",
    "footer": "navigation",
    "search": "search",
    "find": "search",
    "lookup": "search",
    "query": "search",
    "product": "product pages",
    "products": "product pages",
    "catalog": "product pages",
    "shop": "product pages",
    "store": "product pages",
    "listing": "product pages",
    "cart": "checkout",
    "basket": "checkout",
    "checkout": "checkout",
    "purchase": "checkout",
    "buy": "checkout",
    "login": "login",
    "signin": "login",
    "sign-in": "login",
    "auth": "login",
    "account": "login",
    "pricing": "pricing",
    "price": "pricing",
    "plan": "pricing",
    "subscription": "pricing",
    "billing": "pricing",
    "content": "content",
    "article": "content",
    "wiki": "content",
    "documentation": "documentation",
    "docs": "documentation",
    "form": "forms",
    "contact": "forms",
    "submit": "forms",
    "signup": "forms",
    "register": "forms",
    "home": "homepage",
    "homepage": "homepage",
    "landing": "homepage",
    "repository": "repository discovery",
    "repo": "repository discovery",
    "discover": "repository discovery",
    "explore": "repository discovery",
}


def _normalize_theme(text: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", " ", text.lower()).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        return ""
    if cleaned in _THEME_ALIASES:
        return _THEME_ALIASES[cleaned]
    for token in cleaned.split():
        if token in _THEME_ALIASES:
            return _THEME_ALIASES[token]
    return cleaned


def _split_objectives(fragment: str) -> list[str]:
    parts = re.split(r"\s*,\s*|\s+and\s+|\s+&\s+", fragment, flags=re.IGNORECASE)
    return [part.strip() for part in parts if part.strip()]


def _parse_goal_objectives(goal: str) -> list[str]:
    objectives: list[str] = []
    for raw_line in re.split(r"[\n;]+", goal):
        line = raw_line.strip()
        if not line:
            continue
        line = re.sub(r"^[\s•\-*\d.)]+", "", line)
        line = re.sub(r"^verify\s+", "", line, flags=re.IGNORECASE)
        if not line:
            continue
        objectives.extend(_split_objectives(line))
    if not objectives and goal.strip():
        objectives = _split_objectives(goal)
    normalized: list[str] = []
    seen: set[str] = set()
    for item in objectives:
        theme = _normalize_theme(item)
        if theme and theme not in seen:
            seen.add(theme)
            normalized.append(theme)
    return normalized


def _themes_from_text(text: str) -> set[str]:
    themes: set[str] = set()
    for fragment in _split_objectives(text):
        theme = _normalize_theme(fragment)
        if theme:
            themes.add(theme)
    if not themes:
        theme = _normalize_theme(text)
        if theme:
            themes.add(theme)
    return themes


def _collect_planner_text(result: dict[str, Any]) -> str:
    parts: list[str] = []
    meta = result.get("ai_plan_metadata") or {}
    parts.extend(str(item) for item in meta.get("generated_journey") or [])
    for step in result.get("ai_plan") or []:
        if isinstance(step, dict):
            parts.append(str(step.get("label") or ""))
            parts.append(str(step.get("target") or ""))
    return " ".join(parts)


def _collect_executed_text(result: dict[str, Any]) -> str:
    parts: list[str] = []
    for step in result.get("steps") or []:
        status = str(step.get("status") or "").lower()
        if status not in {"passed", "success", "completed"}:
            continue
        parts.append(str(step.get("step") or step.get("label") or ""))
        parts.append(str(step.get("action") or ""))
    return " ".join(parts)


def _evaluate_goal_completion_detail(
    result: dict[str, Any],
    *,
    goal: str | None = None,
) -> DimensionEvaluation:
    stated_goal = goal or str(result.get("goal") or "")
    if not stated_goal.strip():
        return DimensionEvaluation(
            score=0.0,
            summary="No testing goal provided; goal completion cannot be measured.",
            weaknesses=["No testing goal was provided."],
            reasoning="Goal completion requires a stated testing objective.",
            recommendations=["Provide a clear testing goal with verifiable objectives."],
        )

    goal_objectives = _parse_goal_objectives(stated_goal)
    if not goal_objectives:
        goal_objectives = [_normalize_theme(stated_goal)]

    planner_text = _collect_planner_text(result)
    executed_text = _collect_executed_text(result)
    planner_themes = _themes_from_text(planner_text)
    executed_themes = _themes_from_text(executed_text)

    verified = [theme for theme in goal_objectives if theme in executed_themes]
    missing = [theme for theme in goal_objectives if theme not in executed_themes]
    planned_outside_goal = sorted(theme for theme in planner_themes if theme not in goal_objectives)

    percentage = (len(verified) / len(goal_objectives)) * 100.0 if goal_objectives else 0.0

    strengths: list[str] = []
    weaknesses: list[str] = []
    for theme in verified:
        strengths.append(f"{theme.title()} verified during execution.")
    for theme in missing:
        weaknesses.append(f"{theme.title()} requested in goal but never executed.")
    for theme in planned_outside_goal[:3]:
        weaknesses.append(f"{theme.title()} was planned but outside the original goal.")

    if not strengths:
        strengths.append("Execution completed, but no goal themes were clearly verified.")
    if not weaknesses:
        weaknesses.append("All stated goal themes were executed.")

    reasoning_parts = [
        f"Goal requested {len(goal_objectives)} objective(s): {', '.join(goal_objectives)}.",
        f"Planner reflected {len(planner_themes)} theme(s); execution verified {len(verified)} of "
        f"{len(goal_objectives)} goal objective(s) ({percentage:.0f}%).",
    ]
    if missing:
        reasoning_parts.append(f"Never executed: {', '.join(missing)}.")
    if planned_outside_goal:
        reasoning_parts.append(f"Outside original goal: {', '.join(planned_outside_goal)}.")

    recommendations: list[str] = []
    if missing:
        recommendations.append(
            f"Add execution steps to verify: {', '.join(missing)}."
        )
    if planned_outside_goal:
        recommendations.append(
            "Align planner output with stated goal themes and remove unrelated journey steps."
        )
    if not recommendations:
        recommendations.append("Goal coverage is complete; maintain this alignment in future runs.")

    summary = (
        f"Goal completion {percentage:.0f}% — verified: {', '.join(verified) or 'none'}; "
        f"missing: {', '.join(missing) or 'none'}."
    )

    return DimensionEvaluation(
        score=round(percentage, 1),
        summary=summary,
        strengths=strengths,
        weaknesses=weaknesses,
        reasoning=" ".join(reasoning_parts),
        recommendations=recommendations,
    )


def evaluate_goal_completion(
    result: dict[str, Any],
    *,
    goal: str | None = None,
) -> tuple[float, str]:
    detail = _evaluate_goal_completion_detail(result, goal=goal)
    return detail.score, detail.summary


def evaluate_goal_completion_detail(
    result: dict[str, Any],
    *,
    goal: str | None = None,
) -> DimensionEvaluation:
    return _evaluate_goal_completion_detail(result, goal=goal)
