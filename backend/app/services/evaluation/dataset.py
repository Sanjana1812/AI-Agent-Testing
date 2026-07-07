"""Load JSON evaluation datasets for benchmark cases."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.evaluation.models import EvaluationCase

_DATASET_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "evaluation"


def dataset_root() -> Path:
    return _DATASET_ROOT


def load_evaluation_case(path: str | Path) -> EvaluationCase:
    file_path = Path(path)
    if not file_path.is_absolute():
        file_path = _DATASET_ROOT / file_path
    payload = json.loads(file_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Evaluation case must be a JSON object: {file_path}")
    return EvaluationCase.from_dict(payload)


def load_all_cases(directory: str | Path | None = None) -> list[EvaluationCase]:
    root = Path(directory) if directory else _DATASET_ROOT
    cases: list[EvaluationCase] = []
    for file_path in sorted(root.glob("*.json")):
        try:
            cases.append(load_evaluation_case(file_path))
        except (json.JSONDecodeError, ValueError):
            continue
    return cases


def find_matching_case(
    *,
    url: str,
    goal: str,
    cases: list[EvaluationCase] | None = None,
) -> EvaluationCase | None:
    catalog = cases if cases is not None else load_all_cases()
    url_norm = url.lower().strip().rstrip("/")
    goal_norm = goal.lower().strip()
    for case in catalog:
        case_url = case.url.lower().strip().rstrip("/")
        if case_url and case_url in url_norm:
            if not case.goal or case.goal.lower().strip() in goal_norm or goal_norm in case.goal.lower():
                return case
    return None


def validate_case_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not payload.get("url"):
        errors.append("url is required")
    if not payload.get("goal"):
        errors.append("goal is required")
    minimum = payload.get("minimum_assertions", 0)
    if not isinstance(minimum, int) or minimum < 0:
        errors.append("minimum_assertions must be a non-negative integer")
    return errors
