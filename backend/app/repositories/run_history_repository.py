"""Orchestrates persisting a complete test execution."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.entities import TestRun
from app.repositories.assertion_repository import AssertionRepository
from app.repositories.base import BaseRepository
from app.repositories.screenshot_repository import ScreenshotRepository
from app.repositories.test_run_repository import TestRunRepository
from app.repositories.test_step_repository import TestStepRepository
from app.repositories.website_context_repository import WebsiteContextRepository

logger = logging.getLogger(__name__)


class RunHistoryRepository(BaseRepository):
    """Persists a full test run graph in a single transaction."""

    def __init__(self, db: Session) -> None:
        super().__init__(db)
        self.test_runs = TestRunRepository(db)
        self.website_contexts = WebsiteContextRepository(db)
        self.test_steps = TestStepRepository(db)
        self.assertions = AssertionRepository(db)
        self.screenshots = ScreenshotRepository(db)

    def save_execution(
        self,
        *,
        result: dict,
        website_context: dict,
        source_url: str,
    ) -> TestRun:
        """
        Persist TestRun, WebsiteContext, TestSteps, Assertions, and Screenshot metadata.

        Args:
            result: Playwright execution payload returned to the API.
            website_context: Structured Website Context JSON.
            source_url: Original URL submitted for the test run.
        """
        completed_at = datetime.now(timezone.utc)
        duration_ms = int(result.get("duration_ms", 0))
        started_at = completed_at - timedelta(milliseconds=duration_ms)

        run = self.test_runs.create(
            run_id=result["id"],
            url=source_url,
            goal=result["goal"],
            planner_source=result.get("ai_plan_source", "unknown"),
            status=result.get("status", "failed"),
            page_title=result.get("title", ""),
            http_status=int(result.get("http_status", 0)),
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            execution_intelligence_log=result.get("execution_intelligence_log"),
        )

        self.website_contexts.create(
            run_id=run.id,
            context_json=website_context,
        )

        ai_plan = result.get("ai_plan", [])
        execution_steps = result.get("steps", [])
        capture_step_id: str | None = None

        for index, step_data in enumerate(execution_steps, start=1):
            plan_step = ai_plan[index - 1] if index - 1 < len(ai_plan) else {}
            action = plan_step.get("action", step_data.get("step", "unknown"))
            target = plan_step.get("target")

            step = self.test_steps.create(
                run_id=run.id,
                step_number=index,
                action=str(action),
                target=str(target) if target else None,
                status=step_data.get("status", "skipped"),
                duration_ms=int(step_data.get("duration_ms", 0)),
            )

            if action == "capture":
                capture_step_id = step.id

            for assertion_data in step_data.get("assertions", []):
                self.assertions.create(
                    step_id=step.id,
                    assertion_type=str(assertion_data.get("type", "unknown")),
                    expected=str(assertion_data.get("expected", "")),
                    actual=str(assertion_data.get("actual", "")),
                    passed=bool(assertion_data.get("passed", False)),
                    reason=assertion_data.get("reason"),
                )

        screenshot_path = result.get("screenshot", "")
        if screenshot_path:
            self.screenshots.create(
                run_id=run.id,
                step_id=capture_step_id,
                file_path=screenshot_path,
            )

        self.db.flush()
        logger.info("[RunHistory] Persisted run %s with %d steps", run.id, len(execution_steps))
        return run
