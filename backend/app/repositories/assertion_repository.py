"""CRUD operations for assertions."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.entities import Assertion
from app.repositories.base import BaseRepository


class AssertionRepository(BaseRepository):
    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def create(
        self,
        *,
        step_id: str,
        assertion_type: str,
        expected: str,
        actual: str,
        passed: bool,
        reason: str | None,
    ) -> Assertion:
        assertion = Assertion(
            step_id=step_id,
            type=assertion_type,
            expected=expected,
            actual=actual,
            passed=passed,
            reason=reason,
        )
        self.db.add(assertion)
        self.db.flush()
        return assertion

    def list_by_step_id(self, step_id: str) -> list[Assertion]:
        return self.db.query(Assertion).filter(Assertion.step_id == step_id).all()
