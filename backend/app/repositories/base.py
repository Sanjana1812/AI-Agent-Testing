"""Shared repository utilities."""

from __future__ import annotations

from sqlalchemy.orm import Session


class BaseRepository:
    """Base class for SQLAlchemy repositories."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    def refresh(self, instance) -> None:
        self.db.refresh(instance)
