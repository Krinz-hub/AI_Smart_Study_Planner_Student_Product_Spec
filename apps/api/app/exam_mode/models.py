import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    String,
    Integer,
    Numeric,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.common.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class ExamPlan(Base):
    __tablename__ = "exam_plans"

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
    exam_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("exams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32), default="PROPOSED", nullable=False
    )  # PROPOSED, ACCEPTED, CUSTOMIZED, DISMISSED
    total_topics_covered: Mapped[int] = mapped_column(Integer, nullable=False)
    syllabus_coverage_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False
    )
    target_exam_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    daily_workload_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    workload_ceiling_minutes: Mapped[int] = mapped_column(
        Integer, default=360, nullable=False
    )
    rescue_actions: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, default=dict, nullable=False
    )
    tasks_snapshot: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB, default=list, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
