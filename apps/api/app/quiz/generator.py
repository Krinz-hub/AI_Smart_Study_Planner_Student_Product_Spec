import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy import select, func, Integer
from sqlalchemy.ext.asyncio import AsyncSession


from app.quiz.models import Question, QuizAttempt
from app.documents.models import DocumentChunk
from app.common.logging import get_logger

logger = get_logger("quiz_generator")


class QuestionGenerator:
    """Generates schema-validated questions aligned with Bloom taxonomy and learning objectives."""

    @classmethod
    def generate_candidate_questions(
        cls,
        topic_name: str,
        topic_id: uuid.UUID,
        num_questions: int = 5,
        difficulty: str = "MEDIUM",
        chunks: Optional[List[DocumentChunk]] = None,
    ) -> List[Dict[str, Any]]:
        questions: List[Dict[str, Any]] = []
        pred_diff = Decimal("0.30") if difficulty == "EASY" else (Decimal("0.85") if difficulty == "HARD" else Decimal("0.60"))

        # 1. Grounded questions from course material if chunks available
        if chunks:
            for i, chunk in enumerate(chunks[:num_questions]):
                q_text = f"Based on the course reading on {topic_name}: What is the primary significance of: '{chunk.text[:120]}...'?"
                questions.append(
                    {
                        "topic_id": topic_id,
                        "question_type": "MCQ",
                        "difficulty": difficulty,
                        "predicted_difficulty": pred_diff,
                        "question_text": q_text,
                        "options": [
                            {"key": "A", "text": f"It defines the foundational mechanism of {topic_name}."},
                            {"key": "B", "text": "It acts as a deprecated legacy protocol."},
                            {"key": "C", "text": "It has no impact on system behavior."},
                            {"key": "D", "text": "It only applies to simulated theoretical environments."},
                        ],
                        "correct_answer": {"key": "A", "value": f"It defines the foundational mechanism of {topic_name}."},
                        "explanation": f"According to section {chunk.section_path or 'notes'}, this concept establishes key system functionality.",
                        "source_id": chunk.document_id,
                        "source_chunk_id": chunk.id,
                        "generation_model": "rule-grounded-v1",
                        "generation_version": "v1",
                    }
                )

        # 2. Template / Concept questions to fulfill num_questions
        needed = num_questions - len(questions)
        concept_templates = [
            (
                f"What is the core objective of {topic_name}?",
                [
                    {"key": "A", "text": f"To optimize performance and correctness in {topic_name}."},
                    {"key": "B", "text": "To increase computational complexity arbitrarily."},
                    {"key": "C", "text": "To replace all deterministic algorithms with heuristics."},
                    {"key": "D", "text": "To disable error checking mechanisms."},
                ],
                "A",
                f"The primary goal of {topic_name} is ensuring correctness and performance efficiency.",
            ),
            (
                f"Which of the following is TRUE regarding {topic_name}?",
                [
                    {"key": "A", "text": f"Proper execution of {topic_name} requires satisfying prerequisite state constraints."},
                    {"key": "B", "text": "It can be safely ignored in production architectures."},
                    {"key": "C", "text": "It violates standard mathematical invariants."},
                    {"key": "D", "text": "It is exclusively supported in single-threaded environments."},
                ],
                "A",
                f"Prerequisite state constraints must always be satisfied for {topic_name}.",
            ),
            (
                f"What occurs if {topic_name} encounters edge cases or invalid inputs?",
                [
                    {"key": "A", "text": "System handles exceptions and maintains invariant consistency."},
                    {"key": "B", "text": "System immediately halts without reporting errors."},
                    {"key": "C", "text": "Data is silently corrupted without detection."},
                    {"key": "D", "text": "Memory allocations are doubled indefinitely."},
                ],
                "A",
                "Invariant consistency and robust exception handling prevent cascading failures.",
            ),
            (
                f"True or False: In {topic_name}, retrieval practice and spaced repetition enhance long-term retention.",
                [
                    {"key": "A", "text": "True"},
                    {"key": "B", "text": "False"},
                ],
                "A",
                "Empirical learning science demonstrates spaced repetition enhances memory stability.",
            ),
            (
                f"How does {topic_name} interact with related prerequisite concepts?",
                [
                    {"key": "A", "text": "It builds directly upon foundational principles established by prerequisites."},
                    {"key": "B", "text": "It is completely independent of all academic fundamentals."},
                    {"key": "C", "text": "It replaces foundational math with arbitrary rules."},
                    {"key": "D", "text": "Prerequisites degrade understanding of this topic."},
                ],
                "A",
                "Mastery of prerequisites provides the cognitive schema necessary for topic comprehension.",
            ),
        ]

        for i in range(min(needed, len(concept_templates))):
            tmpl = concept_templates[i]
            questions.append(
                {
                    "topic_id": topic_id,
                    "question_type": "MCQ" if len(tmpl[1]) > 2 else "TRUE_FALSE",
                    "difficulty": difficulty,
                    "predicted_difficulty": pred_diff,
                    "question_text": tmpl[0],
                    "options": tmpl[1],
                    "correct_answer": {"key": tmpl[2]},
                    "explanation": tmpl[3],
                    "generation_model": "concept-template-v1",
                    "generation_version": "v1",
                }
            )

        # Validate Schema
        for q in questions:
            cls.validate_question_schema(q)

        return questions[:num_questions]

    @classmethod
    def validate_question_schema(cls, q: Dict[str, Any]) -> None:
        """Enforces schema consistency, option distinctness, and answer validity."""
        assert "question_text" in q and len(q["question_text"]) > 5
        assert "correct_answer" in q and "key" in q["correct_answer"]
        assert "options" in q and isinstance(q["options"], list)
        keys = [opt["key"] for opt in q["options"]]
        texts = [opt["text"].strip().lower() for opt in q["options"]]
        assert q["correct_answer"]["key"] in keys, "Correct answer key must match one of the options"
        assert len(texts) == len(set(texts)), "Options must not contain duplicate distractors"


async def recalibrate_question_difficulty(
    db: AsyncSession,
    question_id: uuid.UUID,
) -> Optional[Decimal]:
    """
    Recalibrates predicted difficulty vs observed success rate.
    observed_difficulty = 1.0 - success_rate
    """
    stmt = (
        select(
            func.count(QuizAttempt.id).label("total"),
            func.sum(func.cast(QuizAttempt.is_correct, Integer)).label("correct"),
        )
        .where(QuizAttempt.question_id == question_id)
    )
    res = await db.execute(stmt)
    row = res.first()
    if not row or not row.total or row.total < 3:
        return None

    success_rate = float(row.correct or 0) / float(row.total)
    actual_diff = round(Decimal(str(max(0.0, min(1.0, 1.0 - success_rate)))), 2)

    q_stmt = select(Question).where(Question.id == question_id)
    q_res = await db.execute(q_stmt)
    q = q_res.scalar_one_or_none()
    if q:
        q.actual_difficulty = actual_diff
        await db.commit()
    return actual_diff
