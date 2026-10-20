"""Document ingestion: register → store → extract text → chunk → embed.

Each stage is idempotent. A document already stored (same SHA-256) is not stored or
re-processed again, and embedding can run later, once an embeddings key is configured.
"""

import uuid
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlparse

import structlog
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import DocumentStore
from app.models import Company, DocumentChunk, Filing, SourceDocument
from app.models.company import ReportingBasis
from app.modules.ingestion.pdf import chunk_page, extract_pages, sha256_of
from app.modules.research.clients import Embedder

log = structlog.get_logger()

PRIMARY_HOSTS = ("bseindia.com", "nseindia.com", "nsearchives.nseindia.com")


@dataclass(frozen=True)
class DocumentInput:
    company: Company
    doc_type: str  # annual_report | investor_presentation | earnings_call_transcript | ...
    title: str
    period_end: date
    filing_date: date | None
    url: str | None
    data: bytes
    content_type: str = "application/pdf"


def _is_primary(url: str | None, company: Company) -> bool:
    """Exchange filings and the company's own website are primary sources."""
    if not url:
        return True
    host = urlparse(url).hostname or ""
    if host.endswith(PRIMARY_HOSTS):
        return True
    words = [w.lower() for w in company.name.split() if len(w) > 3]
    return any(w in host for w in words)


async def register_document(
    session: AsyncSession, store: DocumentStore, doc: DocumentInput
) -> SourceDocument:
    digest = sha256_of(doc.data)
    existing = await session.scalar(select(SourceDocument).where(SourceDocument.sha256 == digest))
    if existing is not None:
        return existing

    filing = await session.scalar(
        select(Filing).where(
            Filing.company_id == doc.company.id,
            Filing.filing_type == doc.doc_type,
            Filing.period_end == doc.period_end,
            Filing.basis == ReportingBasis.CONSOLIDATED,
        )
    )
    if filing is None:
        filing = Filing(
            company_id=doc.company.id,
            filing_type=doc.doc_type,
            period_end=doc.period_end,
            filing_date=doc.filing_date,
            basis=ReportingBasis.CONSOLIDATED,
        )
        session.add(filing)
        await session.flush()

    key = f"documents/{doc.company.nse_symbol or doc.company.id}/{digest}.pdf"
    store.put(key, doc.data, doc.content_type)
    source = SourceDocument(
        filing_id=filing.id,
        title=doc.title,
        s3_key=key,
        sha256=digest,
        content_type=doc.content_type,
        source_url=doc.url,
        publisher=urlparse(doc.url).hostname if doc.url else None,
        is_primary=_is_primary(doc.url, doc.company),
        doc_type=doc.doc_type,
        ingestion_status="registered",
    )
    session.add(source)
    await session.flush()
    log.info("document_registered", title=doc.title, sha256=digest[:12])
    return source


async def extract_document(session: AsyncSession, store: DocumentStore, source: SourceDocument) -> int:
    """Extract page text into chunks (replacing any earlier chunks). Returns the chunk count."""
    if source.s3_key is None:
        raise ValueError(f"Document {source.id} has no stored file")
    pages = extract_pages(store.get(source.s3_key))
    await session.execute(delete(DocumentChunk).where(DocumentChunk.source_document_id == source.id))
    index = 0
    for page in pages:
        for text in chunk_page(page):
            session.add(
                DocumentChunk(
                    source_document_id=source.id, page_number=page.page_number, chunk_index=index, text=text
                )
            )
            index += 1
    source.page_count = len(pages)
    source.ingestion_status = "extracted" if index else "failed"
    source.ingestion_error = None if index else "No extractable text (scanned PDF? needs OCR)"
    await session.flush()
    log.info("document_extracted", title=source.title, pages=len(pages), chunks=index)
    return index


async def embed_document(session: AsyncSession, embedder: Embedder, source: SourceDocument) -> int:
    """Embed this document's chunks that have no embedding yet. Returns the number embedded."""
    chunks = list(
        await session.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.source_document_id == source.id, DocumentChunk.embedding.is_(None))
            .order_by(DocumentChunk.chunk_index)
        )
    )
    if chunks:
        vectors = await embedder.embed([c.text for c in chunks], input_type="document")
        for chunk, vector in zip(chunks, vectors, strict=True):
            chunk.embedding = vector
    remaining = await session.scalar(
        select(func.count())
        .select_from(DocumentChunk)
        .where(DocumentChunk.source_document_id == source.id, DocumentChunk.embedding.is_(None))
    )
    if remaining == 0:
        source.ingestion_status = "embedded"
    await session.flush()
    log.info("document_embedded", title=source.title, embedded=len(chunks))
    return len(chunks)


async def company_documents(session: AsyncSession, company_id: uuid.UUID) -> list[SourceDocument]:
    return list(
        await session.scalars(
            select(SourceDocument)
            .join(Filing, SourceDocument.filing_id == Filing.id)
            .where(Filing.company_id == company_id)
            .order_by(Filing.period_end.desc(), SourceDocument.title)
        )
    )
