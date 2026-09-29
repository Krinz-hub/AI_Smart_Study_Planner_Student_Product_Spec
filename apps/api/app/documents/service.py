import hashlib
import os
import uuid
from typing import List, Optional, Tuple
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.documents.models import Document, DocumentChunk
from app.documents.parser import DocumentParser
from app.documents.chunker import DocumentChunker
from app.documents.embeddings import get_embedding_provider
from app.documents.schemas import (
    DocumentResponse,
    DocumentStatusResponse,
    DocumentChunkResponse,
)
from app.learner.models import LearnerEvent
from app.common.errors import NotFoundException, InvalidRequestException
from app.common.logging import get_logger

logger = get_logger("document_service")

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


async def upload_and_process_document(
    db: AsyncSession,
    user_id: uuid.UUID,
    filename: str,
    content: bytes,
    mime_type: str,
    subject_id: Optional[uuid.UUID] = None,
) -> Document:
    if not content:
        raise InvalidRequestException("Uploaded file cannot be empty")
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise InvalidRequestException("File exceeds maximum size of 50 MB")

    content_hash = hashlib.sha256(content).hexdigest()
    storage_key = f"storage/docs/{user_id}/{content_hash}/{filename}"

    # Deduplication check
    existing_stmt = select(Document).where(
        Document.user_id == user_id,
        Document.content_hash == content_hash,
    )
    existing_res = await db.execute(existing_stmt)
    existing_doc = existing_res.scalar_one_or_none()

    if existing_doc and existing_doc.processing_status == "COMPLETED":
        logger.info(
            "document_deduplicated_reused",
            document_id=str(existing_doc.id),
            user_id=str(user_id),
            content_hash=content_hash,
        )
        return existing_doc

    doc = Document(
        user_id=user_id,
        subject_id=subject_id,
        filename=filename,
        content_hash=content_hash,
        version=1 if not existing_doc else existing_doc.version + 1,
        storage_key=storage_key,
        mime_type=mime_type,
        size_bytes=len(content),
        processing_status="PROCESSING",
        processing_version="v1",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    try:
        # 1. Parse document structure
        sections = DocumentParser.parse(content, filename, mime_type)

        # 2. Chunk sections
        chunker = DocumentChunker()
        chunks = chunker.chunk_sections(sections)

        if not chunks:
            # Fallback if no text extracted
            chunks = [
                chunker._create_chunk(
                    chunk_idx=0,
                    text=f"Document {filename} with no text content.",
                    page_number=1,
                    section_path="root",
                )
            ]

        # 3. Generate dense embeddings
        texts = [c.text for c in chunks]
        provider = get_embedding_provider()
        embeddings = await provider.embed_texts(texts)

        # 4. Insert chunks with pgvector embeddings
        for i, c in enumerate(chunks):
            db_chunk = DocumentChunk(
                document_id=doc.id,
                user_id=user_id,
                chunk_index=c.chunk_index,
                text=c.text,
                page_number=c.page_number,
                section_path=c.section_path,
                metadata_json=c.metadata_json,
                embedding=embeddings[i],
            )
            db.add(db_chunk)

        doc.processing_status = "COMPLETED"
        await db.commit()
        await db.refresh(doc)

        # 5. Record Learner Event (Append-only audit)
        event = LearnerEvent(
            user_id=user_id,
            event_type="DOCUMENT_PROCESSED",
            entity_type="document",
            entity_id=doc.id,
            evidence_category="KNOWLEDGE",
            payload={
                "document_id": str(doc.id),
                "filename": filename,
                "content_hash": content_hash,
                "chunks_count": len(chunks),
                "subject_id": str(subject_id) if subject_id else None,
            },
        )
        db.add(event)
        await db.commit()

        logger.info(
            "document_processing_complete",
            document_id=str(doc.id),
            chunks=len(chunks),
        )
        return doc

    except Exception as e:
        logger.error("document_processing_error", error=str(e), document_id=str(doc.id))
        doc.processing_status = "FAILED"
        doc.error_message = str(e)
        await db.commit()
        await db.refresh(doc)
        return doc


async def get_user_documents(
    db: AsyncSession,
    user_id: uuid.UUID,
    subject_id: Optional[uuid.UUID] = None,
) -> List[DocumentResponse]:
    stmt = (
        select(Document, func.count(DocumentChunk.id).label("chunk_count"))
        .outerjoin(DocumentChunk, DocumentChunk.document_id == Document.id)
        .where(Document.user_id == user_id)
        .group_by(Document.id)
        .order_by(Document.created_at.desc())
    )
    if subject_id:
        stmt = stmt.where(Document.subject_id == subject_id)

    result = await db.execute(stmt)
    rows = result.all()

    responses: List[DocumentResponse] = []
    for doc, count in rows:
        resp = DocumentResponse(
            id=doc.id,
            user_id=doc.user_id,
            subject_id=doc.subject_id,
            filename=doc.filename,
            content_hash=doc.content_hash,
            version=doc.version,
            mime_type=doc.mime_type,
            size_bytes=doc.size_bytes,
            processing_status=doc.processing_status,
            processing_version=doc.processing_version,
            error_message=doc.error_message,
            chunk_count=count,
            created_at=doc.created_at,
        )
        responses.append(resp)
    return responses


async def get_document_by_id(
    db: AsyncSession,
    user_id: uuid.UUID,
    document_id: uuid.UUID,
) -> DocumentResponse:
    stmt = (
        select(Document, func.count(DocumentChunk.id).label("chunk_count"))
        .outerjoin(DocumentChunk, DocumentChunk.document_id == Document.id)
        .where(Document.id == document_id, Document.user_id == user_id)
        .group_by(Document.id)
    )
    result = await db.execute(stmt)
    row = result.first()
    if not row:
        raise NotFoundException("Document not found")

    doc, count = row
    return DocumentResponse(
        id=doc.id,
        user_id=doc.user_id,
        subject_id=doc.subject_id,
        filename=doc.filename,
        content_hash=doc.content_hash,
        version=doc.version,
        mime_type=doc.mime_type,
        size_bytes=doc.size_bytes,
        processing_status=doc.processing_status,
        processing_version=doc.processing_version,
        error_message=doc.error_message,
        chunk_count=count,
        created_at=doc.created_at,
    )


async def get_document_status(
    db: AsyncSession,
    user_id: uuid.UUID,
    document_id: uuid.UUID,
) -> DocumentStatusResponse:
    stmt = (
        select(Document, func.count(DocumentChunk.id).label("chunk_count"))
        .outerjoin(DocumentChunk, DocumentChunk.document_id == Document.id)
        .where(Document.id == document_id, Document.user_id == user_id)
        .group_by(Document.id)
    )
    result = await db.execute(stmt)
    row = result.first()
    if not row:
        raise NotFoundException("Document not found")

    doc, count = row
    return DocumentStatusResponse(
        document_id=doc.id,
        processing_status=doc.processing_status,
        chunk_count=count,
        error_message=doc.error_message,
    )


async def delete_document(
    db: AsyncSession,
    user_id: uuid.UUID,
    document_id: uuid.UUID,
) -> None:
    stmt = select(Document).where(Document.id == document_id, Document.user_id == user_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundException("Document not found")

    # Cascades to document_chunks automatically
    await db.delete(doc)
    await db.commit()
    logger.info("document_deleted", document_id=str(document_id), user_id=str(user_id))


async def get_document_chunks_list(
    db: AsyncSession,
    user_id: uuid.UUID,
    document_id: uuid.UUID,
) -> List[DocumentChunkResponse]:
    # Ensure ownership
    stmt = select(Document).where(Document.id == document_id, Document.user_id == user_id)
    doc_res = await db.execute(stmt)
    if not doc_res.scalar_one_or_none():
        raise NotFoundException("Document not found")

    chunk_stmt = (
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id, DocumentChunk.user_id == user_id)
        .order_by(DocumentChunk.chunk_index)
    )
    res = await db.execute(chunk_stmt)
    chunks = list(res.scalars().all())
    return [DocumentChunkResponse.model_validate(c) for c in chunks]
