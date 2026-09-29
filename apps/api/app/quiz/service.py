import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.academics.models import Topic
from app.documents.models import Document, DocumentChunk
from app.quiz.models import Question, Quiz, QuizAttempt
from app.quiz.generator import QuestionGenerator, recalibrate_question_difficulty
from app.quiz.schemas import (
    QuizGenerateRequest,
    QuizResponse,
    QuestionStudentView,
    QuestionOptionResponse,
    QuizSubmitRequest,
    QuizResultResponse,
    QuestionResultItem,
)
from app.learner.intelligence_service import process_knowledge_observation
from app.learner.models import LearnerEvent
from app.common.errors import NotFoundException, InvalidRequestException
from app.common.logging import get_logger

logger = get_logger("quiz_service")


async def create_quiz(
    db: AsyncSession,
    user_id: uuid.UUID,
    req: QuizGenerateRequest,
) -> QuizResponse:
    # 1. Verify Topic existence
    topic_stmt = select(Topic).where(Topic.id == req.topic_id)
    topic_res = await db.execute(topic_stmt)
    topic = topic_res.scalar_one_or_none()
    if not topic:
        raise NotFoundException("Topic not found")

    # 2. Fetch relevant document chunks if available
    chunk_stmt = (
        select(DocumentChunk)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(
            DocumentChunk.user_id == user_id,
            Document.subject_id == topic.subject_id,
        )
        .limit(10)
    )
    chunk_res = await db.execute(chunk_stmt)
    chunks = list(chunk_res.scalars().all())

    # 3. Generate candidate questions
    candidates = QuestionGenerator.generate_candidate_questions(
        topic_name=topic.name,
        topic_id=topic.id,
        num_questions=req.num_questions,
        difficulty=req.difficulty,
        chunks=chunks if chunks else None,
    )

    # 4. Persist questions and Quiz
    created_questions: List[Question] = []
    for c in candidates:
        q = Question(
            topic_id=req.topic_id,
            question_type=c["question_type"],
            difficulty=c["difficulty"],
            predicted_difficulty=c["predicted_difficulty"],
            question_text=c["question_text"],
            options=c["options"],
            correct_answer=c["correct_answer"],
            explanation=c["explanation"],
            source_id=c.get("source_id"),
            source_chunk_id=c.get("source_chunk_id"),
            generation_model=c.get("generation_model"),
            generation_version=c.get("generation_version"),
        )
        db.add(q)
        created_questions.append(q)

    await db.commit()
    for q in created_questions:
        await db.refresh(q)

    quiz = Quiz(
        user_id=user_id,
        topic_id=req.topic_id,
        status="GENERATED",
        total_questions=len(created_questions),
    )
    db.add(quiz)
    await db.commit()
    await db.refresh(quiz)

    # 5. Build student view (hiding answers)
    student_views: List[QuestionStudentView] = []
    for q in created_questions:
        opts = (
            [QuestionOptionResponse(key=o["key"], text=o["text"]) for o in q.options]
            if q.options
            else None
        )
        student_views.append(
            QuestionStudentView(
                id=q.id,
                question_text=q.question_text,
                question_type=q.question_type,
                difficulty=q.difficulty,
                options=opts,
            )
        )

    return QuizResponse(
        quiz_id=quiz.id,
        id=quiz.id,
        topic_id=quiz.topic_id,
        status=quiz.status,
        total_questions=quiz.total_questions,
        questions=student_views,
    )


async def start_quiz(
    db: AsyncSession,
    user_id: uuid.UUID,
    quiz_id: uuid.UUID,
) -> QuizResponse:
    stmt = select(Quiz).where(Quiz.id == quiz_id, Quiz.user_id == user_id)
    res = await db.execute(stmt)
    quiz = res.scalar_one_or_none()
    if not quiz:
        raise NotFoundException("Quiz not found")

    quiz.status = "IN_PROGRESS"
    await db.commit()
    await db.refresh(quiz)

    # Fetch questions for this topic (most recent first)
    q_stmt = (
        select(Question)
        .where(Question.topic_id == quiz.topic_id)
        .order_by(Question.created_at.desc())
        .limit(quiz.total_questions)
    )
    q_res = await db.execute(q_stmt)
    questions = list(q_res.scalars().all())

    # Fallback if no questions found
    if not questions:
        topic_res = await db.execute(select(Topic).where(Topic.id == quiz.topic_id))
        topic = topic_res.scalar_one_or_none()
        topic_name = topic.name if topic else "General Assessment"
        candidates = QuestionGenerator.generate_candidate_questions(
            topic_name=topic_name,
            topic_id=quiz.topic_id,
            num_questions=quiz.total_questions or 5,
            difficulty="MEDIUM",
        )
        for c in candidates:
            q = Question(
                topic_id=quiz.topic_id,
                question_type=c["question_type"],
                difficulty=c["difficulty"],
                predicted_difficulty=c["predicted_difficulty"],
                question_text=c["question_text"],
                options=c["options"],
                correct_answer=c["correct_answer"],
                explanation=c["explanation"],
                generation_model="fallback-gen",
                generation_version="v1",
            )
            db.add(q)
            questions.append(q)
        await db.commit()
        for q in questions:
            await db.refresh(q)

    student_views = [
        QuestionStudentView(
            id=q.id,
            question_text=q.question_text,
            question_type=q.question_type,
            difficulty=q.difficulty,
            options=[QuestionOptionResponse(key=o["key"], text=o["text"]) for o in q.options] if q.options else None,
        )
        for q in questions
    ]

    return QuizResponse(
        quiz_id=quiz.id,
        id=quiz.id,
        topic_id=quiz.topic_id,
        status=quiz.status,
        total_questions=len(student_views),
        questions=student_views,
    )


async def evaluate_and_submit_quiz(
    db: AsyncSession,
    user_id: uuid.UUID,
    quiz_id: uuid.UUID,
    req: QuizSubmitRequest,
) -> QuizResultResponse:
    stmt = select(Quiz).where(Quiz.id == quiz_id, Quiz.user_id == user_id)
    res = await db.execute(stmt)
    quiz = res.scalar_one_or_none()
    if not quiz:
        raise NotFoundException("Quiz not found")

    now_utc = datetime.now(timezone.utc)
    result_items: List[QuestionResultItem] = []
    correct_count = 0

    for ans_sub in req.answers:
        q_stmt = select(Question).where(Question.id == ans_sub.question_id)
        q_res = await db.execute(q_stmt)
        question = q_res.scalar_one_or_none()
        if not question:
            continue

        # Check correctness
        student_key = ans_sub.answer.get("key", "").strip().upper()
        correct_key = question.correct_answer.get("key", "").strip().upper()
        is_corr = student_key == correct_key

        if is_corr:
            correct_count += 1

        # Record attempt
        attempt = QuizAttempt(
            quiz_id=quiz.id,
            user_id=user_id,
            question_id=question.id,
            answer=ans_sub.answer,
            is_correct=is_corr,
            response_time_seconds=ans_sub.response_time_seconds,
            attempted_at=now_utc,
        )
        db.add(attempt)

        # Recalibrate difficulty asynchronously/empirically
        await recalibrate_question_difficulty(db, question.id)

        result_items.append(
            QuestionResultItem(
                question_id=question.id,
                question_text=question.question_text,
                student_answer=ans_sub.answer,
                correct_answer=question.correct_answer,
                is_correct=is_corr,
                explanation=question.explanation,
            )
        )

    total_submitted = max(1, len(req.answers))
    score = round(correct_count / total_submitted, 3)
    accuracy = score

    quiz.status = "COMPLETED"
    quiz.score = Decimal(str(score))
    quiz.accuracy = Decimal(str(accuracy))
    quiz.time_spent_seconds = req.time_spent_seconds or 0
    quiz.completed_at = now_utc
    await db.commit()
    await db.refresh(quiz)

    # CRITICAL: Authoritative BKT & FSRS update via Learner Intelligence
    is_overall_pass = score >= 0.70
    await process_knowledge_observation(
        db,
        user_id=user_id,
        topic_id=quiz.topic_id,
        is_correct=is_overall_pass,
        response_time_seconds=req.time_spent_seconds,
    )

    # Determine weak/strong concepts
    weak_concepts = []
    strong_concepts = []
    for item in result_items:
        if not item.is_correct:
            weak_concepts.append(item.question_text[:60] + "...")
        else:
            strong_concepts.append(item.question_text[:60] + "...")

    rec_action = "PRACTICE" if score < 0.70 else "ADVANCE_TO_NEXT_TOPIC"

    # Emit QUIZ_COMPLETED event
    event = LearnerEvent(
        user_id=user_id,
        event_type="QUIZ_COMPLETED",
        entity_type="quiz",
        entity_id=quiz.id,
        evidence_category="KNOWLEDGE",
        payload={
            "quiz_id": str(quiz.id),
            "topic_id": str(quiz.topic_id),
            "score": score,
            "accuracy": accuracy,
            "total_questions": len(result_items),
            "correct_count": correct_count,
            "weak_concepts": weak_concepts,
        },
    )
    db.add(event)
    await db.commit()

    return QuizResultResponse(
        quiz_id=quiz.id,
        topic_id=quiz.topic_id,
        score=score,
        accuracy=accuracy,
        total_questions=len(result_items),
        correct_count=correct_count,
        time_spent_seconds=quiz.time_spent_seconds,
        weak_concepts=weak_concepts,
        strong_concepts=strong_concepts,
        recommended_next_action=rec_action,
        questions=result_items,
    )


async def get_quiz_results(
    db: AsyncSession,
    user_id: uuid.UUID,
    quiz_id: uuid.UUID,
) -> QuizResultResponse:
    stmt = (
        select(Quiz)
        .options(selectinload(Quiz.attempts).selectinload(QuizAttempt.question))
        .where(Quiz.id == quiz_id, Quiz.user_id == user_id)
    )
    res = await db.execute(stmt)
    quiz = res.scalar_one_or_none()
    if not quiz:
        raise NotFoundException("Quiz not found")

    items: List[QuestionResultItem] = []
    correct_count = 0
    weak = []
    strong = []

    for att in quiz.attempts:
        if att.is_correct:
            correct_count += 1
            strong.append(att.question.question_text[:60] + "...")
        else:
            weak.append(att.question.question_text[:60] + "...")

        items.append(
            QuestionResultItem(
                question_id=att.question.id,
                question_text=att.question.question_text,
                student_answer=att.answer,
                correct_answer=att.question.correct_answer,
                is_correct=att.is_correct,
                explanation=att.question.explanation,
            )
        )

    score = float(quiz.score or Decimal("0.0"))
    return QuizResultResponse(
        quiz_id=quiz.id,
        topic_id=quiz.topic_id,
        score=score,
        accuracy=float(quiz.accuracy or Decimal("0.0")),
        total_questions=quiz.total_questions,
        correct_count=correct_count,
        time_spent_seconds=quiz.time_spent_seconds,
        weak_concepts=weak,
        strong_concepts=strong,
        recommended_next_action="PRACTICE" if score < 0.70 else "ADVANCE",
        questions=items,
    )
