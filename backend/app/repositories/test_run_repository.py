"""CRUD operations for test runs."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.entities import TestRun, TestStep
from app.repositories.base import BaseRepository


class TestRunRepository(BaseRepository):
    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def create(
        self,
        *,
        run_id: str,
        url: str,
        goal: str,
        planner_source: str,
        status: str,
        page_title: str,
        http_status: int,
        started_at: datetime,
        completed_at: datetime,
        duration_ms: int,
    ) -> TestRun:
        run = TestRun(
            id=run_id,
            url=url,
            goal=goal,
            planner_source=planner_source,
            status=status,
            page_title=page_title,
            http_status=http_status,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
        )
        self.db.add(run)
        self.db.flush()
        return run

    def get_by_id(self, run_id: str) -> TestRun | None:
        return self.db.get(TestRun, run_id)

    def get_with_details(self, run_id: str) -> TestRun | None:
        stmt = (
            select(TestRun)
            .options(
                joinedload(TestRun.website_context),
                joinedload(TestRun.steps).joinedload(TestStep.assertions),
                joinedload(TestRun.screenshots),
            )
            .where(TestRun.id == run_id)
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def list_recent(self, limit: int = 50, offset: int = 0) -> list[TestRun]:
        stmt = select(TestRun).order_by(TestRun.created_at.desc()).limit(limit).offset(offset)
        return list(self.db.scalars(stmt).all())

    def delete(self, run_id: str) -> bool:
        run = self.get_by_id(run_id)
        if not run:
            return False
        self.db.delete(run)
        self.db.flush()
        return True
