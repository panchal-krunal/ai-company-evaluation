"""Semantic retrieval over a company's embedded document chunks, and quote verification."""

import re
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DocumentChunk, Filing, SourceDocument
from app.modules.research.clients import Embedder


@dataclass(frozen=True)
class Passage:
    passage_id: str  # "P1", "P2", … — what the model cites
    chunk_id: str
    source_document_id: str
    document_title: str
    doc_type: str | None
    page_number: int | None
    text: str


async def count_embedded_chunks(session: AsyncSession, company_id: uuid.UUID) -> int:
    rows = await session.scalars(
        select(DocumentChunk.id)
        .join(SourceDocument, DocumentChunk.source_document_id == SourceDocument.id)
        .join(Filing, SourceDocument.filing_id == Filing.id)
        .where(Filing.company_id == company_id, DocumentChunk.embedding.is_not(None))
        .limit(1)
    )
    return len(rows.all())


async def retrieve(
    session: AsyncSession,
    embedder: Embedder,
    company_id: uuid.UUID,
    queries: list[str],
    *,
    per_query: int,
    max_passages: int,
    doc_types: list[str] | None = None,
) -> list[Passage]:
    """Top passages for each query (cosine distance), de-duplicated, labelled P1…Pn."""
    vectors = await embedder.embed(queries, input_type="query")
    seen: dict[uuid.UUID, tuple[DocumentChunk, SourceDocument]] = {}
    for vector in vectors:
        stmt = (
            select(DocumentChunk, SourceDocument)
            .join(SourceDocument, DocumentChunk.source_document_id == SourceDocument.id)
            .join(Filing, SourceDocument.filing_id == Filing.id)
            .where(Filing.company_id == company_id, DocumentChunk.embedding.is_not(None))
            .order_by(DocumentChunk.embedding.cosine_distance(vector))
            .limit(per_query)
        )
        if doc_types:
            stmt = stmt.where(SourceDocument.doc_type.in_(doc_types))
        for chunk, doc in await session.execute(stmt):
            seen.setdefault(chunk.id, (chunk, doc))
            if len(seen) >= max_passages:
                break
    return [
        Passage(
            passage_id=f"P{i}",
            chunk_id=str(chunk.id),
            source_document_id=str(doc.id),
            document_title=doc.title,
            doc_type=doc.doc_type,
            page_number=chunk.page_number,
            text=chunk.text,
        )
        for i, (chunk, doc) in enumerate(seen.values(), start=1)
    ]


def format_passages(passages: list[Passage]) -> str:
    return "\n\n".join(
        f'<passage id="{p.passage_id}" document="{p.document_title}" page="{p.page_number}">\n{p.text}\n</passage>'
        for p in passages
    )


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def verify_quote(passages: dict[str, Passage], passage_id: str, quote: str) -> Passage | None:
    """Return the cited passage if the quote appears in it verbatim (ignoring whitespace and case)."""
    passage = passages.get(passage_id)
    needle = _normalise(quote)
    if passage is None or len(needle) < 8:
        return None
    return passage if needle in _normalise(passage.text) else None


def evidence_entry(passage: Passage | None, passage_id: str, quote: str) -> dict[str, object]:
    return {
        "passage_id": passage_id,
        "quote": quote,
        "verified": passage is not None,
        "source_document_id": passage.source_document_id if passage else None,
        "document_title": passage.document_title if passage else None,
        "page_number": passage.page_number if passage else None,
    }
