"""Ingest downloaded documents: register + store, extract text, and embed (when a Voyage key is set).

Reads storage/inbox/manifest.json (written when the documents were downloaded). Safe to re-run:
stored documents are skipped, and only chunks without embeddings are embedded.

Usage:
    uv run python -m scripts.ingest_documents                 # all companies in the manifest
    uv run python -m scripts.ingest_documents --symbol CUPID  # one company
"""

import argparse
import asyncio
import json
from datetime import date
from pathlib import Path

import structlog
from sqlalchemy import select

from app.core.database import SessionLocal, engine, init_db
from app.core.logging import configure_logging
from app.core.storage import get_store
from app.models import Company
from app.modules.ingestion.pipeline import DocumentInput, embed_document, extract_document, register_document
from app.modules.research.clients import AIConfigurationError, Embedder, VoyageEmbedder

log = structlog.get_logger()
INBOX = Path("storage/inbox")


async def main(symbol: str | None) -> None:
    await init_db()
    entries = json.loads((INBOX / "manifest.json").read_text())
    if symbol:
        entries = [e for e in entries if e["nse_symbol"] == symbol]
    store = get_store()
    embedder: Embedder | None
    try:
        embedder = VoyageEmbedder()
    except AIConfigurationError as exc:
        embedder = None
        log.warning("embedding_skipped", reason=str(exc))

    for entry in entries:
        async with SessionLocal() as session:
            company = await session.scalar(select(Company).where(Company.nse_symbol == entry["nse_symbol"]))
            if company is None:
                log.warning("company_missing", symbol=entry["nse_symbol"])
                continue
            source = await register_document(
                session,
                store,
                DocumentInput(
                    company=company,
                    doc_type=entry["doc_type"],
                    title=entry["title"],
                    period_end=date.fromisoformat(entry["period_end"]),
                    filing_date=date.fromisoformat(entry["filing_date"])
                    if entry.get("filing_date")
                    else None,
                    url=entry.get("url"),
                    data=(INBOX / entry["file"]).read_bytes(),
                ),
            )
            if source.ingestion_status == "registered":
                await extract_document(session, store, source)
                await session.commit()
            if embedder is not None and source.ingestion_status == "extracted":
                await embed_document(session, embedder, source)
            await session.commit()
            log.info(
                "document_ready", title=source.title, status=source.ingestion_status, pages=source.page_count
            )
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol")
    configure_logging(debug=True)
    asyncio.run(main(parser.parse_args().symbol))
