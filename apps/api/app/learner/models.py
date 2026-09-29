import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional
from sqlalchemy import (
    String,
    DateTime,
    ForeignKey,
    Text,
    Numeric,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.common.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class LearnerEvent(Base):
    __tablename__ = "learner_events"

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
    event_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    evidence_category: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="BEHAVIOR",
    )
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        unique=True,
        index=True,
    )
    payload: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        index=True,
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actor_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="student",
    )
    action: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    entity_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class MasteryState(Base):
    __tablename__ = "mastery_states"
    __table_args__ = (
        UniqueConstraint("user_id", "topic_id", name="uq_mastery_user_topic"),
    )

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
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mastery_probability: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), default=Decimal("0.100"), nullable=False
    )
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), default=Decimal("0.000"), nullable=False
    )
    evidence_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    state: Mapped[str] = mapped_column(
        String(32), default="UNKNOWN", nullable=False
    )  # UNKNOWN, CRITICAL, WEAK, DEVELOPING, STRONG, MASTERED
    model_version: Mapped[str] = mapped_column(
        String(32), default="bkt-v1", nullable=False
    )
    last_assessed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class MemoryState(Base):
    __tablename__ = "memory_states"
    __table_args__ = (
        UniqueConstraint("user_id", "topic_id", name="uq_memory_user_topic"),
    )

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
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stability: Mapped[Decimal] = mapped_column(
        Numeric(8, 2), default=Decimal("1.00"), nullable=False
    )  # in days
    difficulty: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), default=Decimal("5.00"), nullable=False
    )  # 1.0 to 10.0
    retrievability: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), default=Decimal("1.000"), nullable=False
    )  # 0.0 to 1.0
    next_review_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    fsrs_version: Mapped[str] = mapped_column(
        String(32), default="fsrs-v4", nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class ConfidenceState(Base):
    __tablename__ = "confidence_states"
    __table_args__ = (
        UniqueConstraint("user_id", "topic_id", name="uq_confidence_user_topic"),
    )

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
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    self_confidence: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), default=Decimal("0.500"), nullable=False
    )  # 0.0 to 1.0
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
