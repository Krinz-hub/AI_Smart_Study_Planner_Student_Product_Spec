import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.academics.models import Topic, Subject
from app.learner.models import MasteryState, LearnerEvent
from app.learner.gaps import detect_knowledge_gaps
from app.rag.service import search_and_rank
from app.rag.schemas import RetrievalSearchRequest
from app.tutor.schemas import TutorChatRequest, TutorChatResponse
from app.ai.google_provider import generate_text
from app.common.errors import NotFoundException
from app.common.logging import get_logger

logger = get_logger("tutor_service")


async def generate_tutor_response(
    db: AsyncSession,
    user_id: uuid.UUID,
    req: TutorChatRequest,
) -> TutorChatResponse:
    # 1. Fetch Topic with subject eagerly loaded to avoid greenlet IO
    stmt = (
        select(Topic)
        .options(joinedload(Topic.subject))
        .where(Topic.id == req.topic_id)
    )
    res = await db.execute(stmt)
    topic = res.scalar_one_or_none()
    if not topic:
        raise NotFoundException("Topic not found")

    # 2. Fetch Learner State (Mastery & Gaps)
    mastery_stmt = select(MasteryState).where(
        MasteryState.user_id == user_id,
        MasteryState.topic_id == req.topic_id,
    )
    mastery_res = await db.execute(mastery_stmt)
    mastery = mastery_res.scalar_one_or_none()
    mastery_state = mastery.state if mastery else "UNKNOWN"
    mastery_prob = float(mastery.mastery_probability) if mastery else 0.1

    gaps = await detect_knowledge_gaps(db, user_id, req.topic_id)
    gap_types = [g["gap_type"] for g in gaps]

    # 3. Retrieve Course Evidence Chunks (Tenant Isolated)
    rag_res = await search_and_rank(
        db,
        user_id=user_id,
        req=RetrievalSearchRequest(
            query=req.message,
            subject_id=topic.subject_id,
            topic_id=topic.id,
            limit=3,
        ),
    )

    # 4. Construct Pedagogical Mode Response
    mode = req.mode
    citations_text = ""
    if rag_res.sources:
        citations_text = " (Referenced from: " + ", ".join([f"[{s.source_id}] {s.document_title}" for s in rag_res.sources]) + ")"

    if mode == "socratic":
        pedagogical_intent = "guide_with_leading_question"
        if rag_res.sources:
            response_text = (
                f"Let's explore {topic.name} step by step. Considering your course material {citations_text}: "
                f"What happens to the system state when you apply this principle to: '{req.message}'? "
                f"What would be the immediate consequence if that assumption didn't hold?"
            )
        else:
            response_text = (
                f"To understand {topic.name}, consider the core invariant. "
                f"When you look at '{req.message}', which fundamental constraint must always be preserved?"
            )
        followups = [
            f"How does this relate to the main objective of {topic.name}?",
            "What edge case could break this behavior?",
        ]

    elif mode == "explain_simply":
        pedagogical_intent = "conceptual_simplification"
        response_text = (
            f"Think of {topic.name} like an organized dispatch system. "
            f"When you have '{req.message}', instead of doing everything at once, "
            f"the system coordinates the steps sequentially to prevent bottlenecking.{citations_text}"
        )
        followups = ["Can you give me a real-world example?", "How is this different from brute force?"]

    elif mode == "explain_in_detail":
        pedagogical_intent = "deep_technical_mechanics"
        response_text = (
            f"Technical breakdown for {topic.name}:\n"
            f"1. Invariant Definition: System guarantees correctness under specified precondition.\n"
            f"2. Execution Flow: Operates through state transitions addressing '{req.message}'.\n"
            f"3. Complexity & Constraints: Maintains optimal bounds while preventing starvation.{citations_text}"
        )
        followups = ["What are the mathematical proofs behind this?", "How does memory allocation behave here?"]

    elif mode == "give_example":
        pedagogical_intent = "worked_example_walkthrough"
        response_text = (
            f"Here is a concrete worked example for {topic.name}:\n"
            f"Given initial state S0 with input corresponding to '{req.message}':\n"
            f"Step 1: Validate input constraints.\n"
            f"Step 2: Transition through intermediate state S1.\n"
            f"Step 3: Reach target terminal state S_final successfully.{citations_text}"
        )
        followups = ["Could you walk through a negative test case?", "Try asking me a problem to solve."]

    elif mode == "exam_answer":
        pedagogical_intent = "exam_marking_rubric_format"
        response_text = (
            f"Exam-Ready Solution Structure for {topic.name}:\n"
            f"• Core Definition: Precise definition of {topic.name}.\n"
            f"• Key Equations/Mechanisms: Direct response to '{req.message}'.\n"
            f"• Key Terminology: High-scoring rubric points and trade-offs.{citations_text}"
        )
        followups = ["What are common deduction traps on this question?", "Give me a practice exam question."]

    elif mode == "hint":
        pedagogical_intent = "minimal_scaffolding"
        response_text = (
            f"Hint for {topic.name}: Look at the first operation required by '{req.message}'. "
            f"Which component is responsible for initiating that transition?{citations_text}"
        )
        followups = ["I think it's the controller, is that right?", "Give me another small hint."]

    elif mode == "correct_my_answer":
        pedagogical_intent = "error_diagnostic_and_remediation"
        response_text = (
            f"Evaluating your answer regarding {topic.name}:\n"
            f"• Strengths: Good intuition regarding the initial mechanism in '{req.message}'.\n"
            f"• Refinement Needed: Ensure prerequisite conditions and edge cases are explicitly accounted for.{citations_text}"
        )
        followups = ["How should I rephrase the final conclusion?", "Can I try another attempt?"]

    else:
        pedagogical_intent = "general_academic_guidance"
        response_text = f"Regarding {topic.name}: '{req.message}'.{citations_text}"
        followups = ["Tell me more", "Quiz me on this"]

    # 4.1 Enhance with LLM generation if available (Gemini or Ollama lite model fallback)
    try:
        subject_name = topic.subject.name if getattr(topic, "subject", None) else "Curriculum"
        llm_prompt = (
            f"Subject: {subject_name}\n"
            f"Topic: {topic.name}\n"
            f"Instructional Mode: {mode}\n"
            f"Student Question: {req.message}\n"
            f"Course Materials Reference: {citations_text if citations_text else 'None'}\n\n"
            f"Respond concisely as an expert academic tutor adhering to the '{mode}' pedagogical mode."
        )
        ai_resp = await generate_text(
            prompt=llm_prompt,
            system_instruction=f"You are an encouraging, expert academic tutor specialized in {topic.name}."
        )
        if ai_resp and len(ai_resp.strip()) > 15:
            response_text = ai_resp.strip()
    except Exception as e:
        logger.debug("tutor_llm_generation_skipped", error=str(e))

    # Guarantee mode invariants
    if mode == "socratic" and "?" not in response_text:
        response_text += f"\n\nWhat do you consider to be the primary role of this concept in {topic.name}?"
    elif mode == "exam_answer" and "Exam-Ready Solution Structure" not in response_text:
        response_text = f"Exam-Ready Solution Structure for {topic.name}:\n\n" + response_text

    # Guarantee source citations in response text if sources are present
    if rag_res.sources:
        titles_in_text = any(
            getattr(s, "document_title", "") in response_text
            for s in rag_res.sources
            if getattr(s, "document_title", None)
        )
        if not titles_in_text:
            source_titles = [f"- {getattr(s, 'document_title', 'Course Note')}" for s in rag_res.sources]
            response_text += "\n\n**Sources:**\n" + "\n".join(source_titles)

    # 5. Emit Learner Event (Append-only behavior tracking)
    # Tutor NEVER directly mutates MasteryState
    event = LearnerEvent(
        user_id=user_id,
        event_type="TUTOR_INTERACTION",
        entity_type="topic",
        entity_id=topic.id,
        evidence_category="BEHAVIOR",
        payload={
            "topic_id": str(topic.id),
            "mode": mode,
            "pedagogical_intent": pedagogical_intent,
            "sources_count": len(rag_res.sources),
        },
    )
    db.add(event)
    await db.commit()

    return TutorChatResponse(
        topic_id=topic.id,
        mode=mode,
        response_text=response_text,
        sources=rag_res.sources,
        evidence_sufficiency=rag_res.sufficiency,
        pedagogical_intent=pedagogical_intent,
        suggested_followups=followups,
    )
