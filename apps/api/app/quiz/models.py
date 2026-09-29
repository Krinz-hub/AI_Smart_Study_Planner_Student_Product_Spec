import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    String,
    Text,
    Boolean,
    Integer,
    Numeric,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.common.database import Base
import app.auth.models  # noqa: F401
import app.academics.models  # noqa: F401
import app.documents.models  # noqa: F401


def utc_now():
    return datetime.now(timezone.utc)


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # MCQ, TRUE_FALSE, FILL_BLANK, SHORT_ANSWER
    difficulty: Mapped[str] = mapped_column(
        String(32), default="MEDIUM", nullable=False, index=True
    )  # EASY, MEDIUM, HARD
    predicted_difficulty: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(3, 2), nullable=True
    )
    actual_difficulty: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(3, 2), nullable=True
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSONB, nullable=True)
    correct_answer: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_chunk_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True,
    )
    generation_model: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    generation_version: Mapped[Optional[str]] = mapped_column(String(32), default="v1", nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    attempts: Mapped[List["QuizAttempt"]] = relationship(
        "QuizAttempt", back_populates="question", cascade="all, delete-orphan"
    )


class Quiz(Base):
    __tablename__ = "quizzes"

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
    status: Mapped[str] = mapped_column(
        String(32), default="GENERATED", nullable=False
    )  # GENERATED, IN_PROGRESS, COMPLETED
    score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 3), nullable=True)
    accuracy: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 3), nullable=True)
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    attempts: Mapped[List["QuizAttempt"]] = relationship(
        "QuizAttempt", back_populates="quiz", cascade="all, delete-orphan"
    )


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    quiz_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("quizzes.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    answer: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    response_time_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    question: Mapped["Question"] = relationship("Question", back_populates="attempts")
    quiz: Mapped[Optional["Quiz"]] = relationship("Quiz", back_populates="attempts")
