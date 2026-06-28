"""CRUD operations for test steps."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.entities import TestStep
from app.repositories.base import BaseRepository


class TestStepRepository(BaseRepository):
    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def create(
        self,
        *,
        run_id: str,
        step_number: int,
        action: str,
        target: str | None,
        status: str,
        duration_ms: int,
    ) -> TestStep:
        step = TestStep(
            run_id=run_id,
            step_number=step_number,
            action=action,
            target=target,
            status=status,
            duration_ms=duration_ms,
        )
        self.db.add(step)
        self.db.flush()
        return step

    def list_by_run_id(self, run_id: str) -> list[TestStep]:
        return (
            self.db.query(TestStep)
            .filter(TestStep.run_id == run_id)
            .order_by(TestStep.step_number)
            .all()
        )
