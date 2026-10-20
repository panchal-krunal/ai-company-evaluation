import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.storage import get_store
from app.models import Company, DocumentChunk, Filing, SourceDocument
from app.modules.research.clients import ai_capabilities
from app.schemas.financials import DocumentRead

router = APIRouter(tags=["documents"])


@router.get("/companies/{company_id}/documents", response_model=list[DocumentRead])
async def company_documents(
    company_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> list[DocumentRead]:
    if await session.get(Company, company_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found")
    chunks = (
        select(
            DocumentChunk.source_document_id,
            func.count().label("chunks"),
            func.count(DocumentChunk.embedding).label("embedded"),
        )
        .group_by(DocumentChunk.source_document_id)
        .subquery()
    )
    rows = await session.execute(
        select(SourceDocument, Filing, chunks.c.chunks, chunks.c.embedded)
        .join(Filing, SourceDocument.filing_id == Filing.id)
        .outerjoin(chunks, chunks.c.source_document_id == SourceDocument.id)
        .where(Filing.company_id == company_id)
        .order_by(Filing.period_end.desc(), SourceDocument.doc_type)
    )
    return [
        DocumentRead.model_validate(doc).model_copy(
            update={
                "period_end": filing.period_end,
                "filing_date": filing.filing_date,
                "chunks": n or 0,
                "embedded_chunks": e or 0,
            }
        )
        for doc, filing, n, e in rows
    ]


@router.get("/documents/{document_id}/file")
async def document_file(document_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> Response:
    """Serve the stored source file (open with #page=N to jump to cited evidence)."""
    doc = await session.get(SourceDocument, document_id)
    if doc is None or doc.s3_key is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document file not available")
    return Response(
        get_store().get(doc.s3_key),
        media_type=doc.content_type,
        headers={"Content-Disposition": f'inline; filename="{doc.title}.pdf"'},
    )


@router.get("/system/capabilities")
async def capabilities() -> dict[str, bool]:
    """Which AI features are configured (keys present), for the dashboard to explain what is off."""
    return ai_capabilities()
