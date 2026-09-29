import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    Numeric,
    Integer,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.common.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class StudyTask(Base):
    __tablename__ = "study_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    task_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # LEARN, PRACTICE, REVISE, RETRIEVE, QUIZ, PREREQUISITE_REPAIR, QUICK_REVISION
    planned_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    planned_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    priority: Mapped[Decimal] = mapped_column(
        Numeric(5, 3), default=Decimal("0.500"), nullable=False
    )
    priority_version: Mapped[str] = mapped_column(
        String(32), default="priority-v1", nullable=False
    )
    reason: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    status: Mapped[str] = mapped_column(
        String(32), default="PENDING", nullable=False, index=True
    )  # PENDING, IN_PROGRESS, COMPLETED, SKIPPED, EXPIRED, CANCELLED
    locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    plan_version: Mapped[str] = mapped_column(
        String(32), default="plan-v1", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    sessions: Mapped[List["StudySession"]] = relationship(
        "StudySession", back_populates="task", cascade="all, delete-orphan"
    )


class StudySession(Base):
    __tablename__ = "study_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("study_tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    actual_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_status: Mapped[str] = mapped_column(
        String(32), default="COMPLETED", nullable=False
    )  # COMPLETED, PARTIAL, ABANDONED
    self_rating: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(3, 2), nullable=True
    )

    task: Mapped["StudyTask"] = relationship("StudyTask", back_populates="sessions")
