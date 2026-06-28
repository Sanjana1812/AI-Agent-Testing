"""CRUD operations for screenshots."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.entities import Screenshot
from app.repositories.base import BaseRepository


class ScreenshotRepository(BaseRepository):
    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def create(
        self,
        *,
        run_id: str,
        step_id: str | None,
        file_path: str,
    ) -> Screenshot:
        screenshot = Screenshot(
            run_id=run_id,
            step_id=step_id,
            file_path=file_path,
        )
        self.db.add(screenshot)
        self.db.flush()
        return screenshot

    def list_by_run_id(self, run_id: str) -> list[Screenshot]:
        return self.db.query(Screenshot).filter(Screenshot.run_id == run_id).all()
