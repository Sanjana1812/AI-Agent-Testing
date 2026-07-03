from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent


class TestRun(Base):
    __tablename__ = "test_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    planner_source: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    page_title: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    http_status: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    execution_intelligence_log: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    website_context: Mapped[WebsiteContext | None] = relationship(
        back_populates="run",
        uselist=False,
        cascade="all, delete-orphan",
    )
    steps: Mapped[list[TestStep]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="TestStep.step_number",
    )
    screenshots: Mapped[list[Screenshot]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )


class WebsiteContext(Base):
    __tablename__ = "website_contexts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("test_runs.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    context_json: Mapped[dict] = mapped_column(JSON, nullable=False)

    run: Mapped[TestRun] = relationship(back_populates="website_context")


class TestStep(Base):
    __tablename__ = "test_steps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("test_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    target: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    run: Mapped[TestRun] = relationship(back_populates="steps")
    assertions: Mapped[list[Assertion]] = relationship(
        back_populates="step",
        cascade="all, delete-orphan",
    )
    screenshots: Mapped[list[Screenshot]] = relationship(back_populates="step")


class Assertion(Base):
    __tablename__ = "assertions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    step_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("test_steps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    expected: Mapped[str] = mapped_column(Text, default="", nullable=False)
    actual: Mapped[str] = mapped_column(Text, default="", nullable=False)
    passed: Mapped[bool] = mapped_column(nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    step: Mapped[TestStep] = relationship(back_populates="assertions")


class Screenshot(Base):
    __tablename__ = "screenshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("test_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("test_steps.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    run: Mapped[TestRun] = relationship(back_populates="screenshots")
    step: Mapped[TestStep | None] = relationship(back_populates="screenshots")
