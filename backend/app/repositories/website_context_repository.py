"""CRUD operations for website context records."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.entities import WebsiteContext
from app.repositories.base import BaseRepository


class WebsiteContextRepository(BaseRepository):
    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def create(self, *, run_id: str, context_json: dict) -> WebsiteContext:
        record = WebsiteContext(run_id=run_id, context_json=context_json)
        self.db.add(record)
        self.db.flush()
        return record

    def get_by_run_id(self, run_id: str) -> WebsiteContext | None:
        return (
            self.db.query(WebsiteContext)
            .filter(WebsiteContext.run_id == run_id)
            .one_or_none()
        )
