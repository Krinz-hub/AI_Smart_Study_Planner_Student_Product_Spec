import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.common.database import get_db
from app.documents.schemas import (
    DocumentUploadResponse,
    DocumentResponse,
    DocumentStatusResponse,
    DocumentChunkResponse,
    Document10PointSummary,
    DocumentFlashcardsResponse,
    NoteGroundedQuizGenerateRequest,
)
from app.documents.service import (
    upload_and_process_document,
    get_user_documents,
    get_document_by_id,
    get_document_status,
    delete_document,
    get_document_chunks_list,
)
from app.documents.summary_service import (
    get_or_generate_document_summary,
    get_document_flashcards,
    generate_note_grounded_quiz,
)
from app.quiz.schemas import QuizResponse

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    subject_id: Optional[uuid.UUID] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    """Uploads and processes document (TXT, PDF, DOCX) into vector chunks with SHA-256 deduplication."""
    content = await file.read()
    filename = file.filename or "uploaded_document.txt"
    mime = file.content_type or "text/plain"

    doc = await upload_and_process_document(
        db=db,
        user_id=current_user.id,
        filename=filename,
        content=content,
        mime_type=mime,
        subject_id=subject_id,
    )

    return DocumentUploadResponse(
        document_id=doc.id,
        processing_status=doc.processing_status,
        content_hash=doc.content_hash,
        filename=doc.filename,
    )


@router.get("", response_model=List[DocumentResponse])
async def list_documents(
    subject_id: Optional[uuid.UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[DocumentResponse]:
    """Lists all tenant-isolated documents for the current user."""
    return await get_user_documents(db, current_user.id, subject_id)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Retrieves document metadata by ID."""
    return await get_document_by_id(db, current_user.id, document_id)


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
async def get_status(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentStatusResponse:
    """Retrieves document processing status and chunk count."""
    return await get_document_status(db, current_user.id, document_id)


@router.get("/{document_id}/chunks", response_model=List[DocumentChunkResponse])
async def list_chunks(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[DocumentChunkResponse]:
    """Retrieves chunks for a document."""
    return await get_document_chunks_list(db, current_user.id, document_id)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deletes document and cascades removal of all chunks and embeddings."""
    await delete_document(db, current_user.id, document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{document_id}/summary", response_model=Document10PointSummary)
@router.post("/{document_id}/summary", response_model=Document10PointSummary)
async def get_document_10_point_summary(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Document10PointSummary:
    """Generates or retrieves comprehensive 10-point learning summary cached in MongoDB."""
    return await get_or_generate_document_summary(db, current_user.id, document_id)


@router.get("/{document_id}/flashcards", response_model=DocumentFlashcardsResponse)
async def get_flashcards(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentFlashcardsResponse:
    """Extracts active recall flashcards from document definitions and concepts."""
    return await get_document_flashcards(db, current_user.id, document_id)


@router.post("/{document_id}/generate-quiz", response_model=QuizResponse)
async def post_generate_note_quiz(
    document_id: uuid.UUID,
    req: NoteGroundedQuizGenerateRequest = NoteGroundedQuizGenerateRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuizResponse:
    """Generates candidate practice quiz strictly grounded in uploaded note chunks with citations."""
    return await generate_note_grounded_quiz(db, current_user.id, document_id, req)

