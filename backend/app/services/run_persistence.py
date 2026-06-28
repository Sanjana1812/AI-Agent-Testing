"""Persists test execution results to the database."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models.entities import TestRun
from app.repositories.run_history_repository import RunHistoryRepository

logger = logging.getLogger(__name__)


class RunPersistenceService:
    """Application service for saving completed test runs."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = RunHistoryRepository(db)

    def persist(
        self,
        *,
        result: dict,
        website_context: dict,
        source_url: str,
    ) -> TestRun | None:
        """
        Save a completed execution to the database.

        Returns the persisted TestRun, or None if persistence failed.
        """
        try:
            run = self.repository.save_execution(
                result=result,
                website_context=website_context,
                source_url=source_url,
            )
            self.db.commit()
            logger.info("[RunPersistence] Saved run %s", run.id)
            return run
        except Exception as exc:
            self.db.rollback()
            logger.error("[RunPersistence] Failed to save run %s: %s", result.get("id"), exc, exc_info=True)
            return None
