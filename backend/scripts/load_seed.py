"""Load a company seed file (company, sources, financial facts) into the database.

Idempotent: re-running updates existing rows instead of duplicating them.

Usage:
    uv run python -m scripts.load_seed data/seeds/ather_energy.json
"""

import asyncio
import json
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal, engine, init_db
from app.core.logging import configure_logging
from app.models import Company, FinancialFact, SourceDocument
from app.models.company import CompanyType, Coverage, ReportingBasis

log = structlog.get_logger()


async def upsert_company(session: AsyncSession, data: dict[str, Any]) -> Company:
    company = await session.scalar(select(Company).where(Company.nse_symbol == data["nse_symbol"]))
    if company is None:
        company = Company(nse_symbol=data["nse_symbol"], coverage=data.get("coverage", Coverage.EVALUATED))
        session.add(company)
    company.name = data["name"]
    company.bse_code = data.get("bse_code")
    company.isin = data.get("isin")
    company.sector = data.get("sector")
    company.company_type = CompanyType(data.get("company_type", "non_financial"))
    # A peer never downgrades a company that is itself under evaluation.
    if data.get("coverage") == Coverage.PEER and company.coverage != Coverage.EVALUATED:
        company.coverage = Coverage.PEER
    elif data.get("coverage", Coverage.EVALUATED) == Coverage.EVALUATED:
        company.coverage = Coverage.EVALUATED
    await session.flush()
    return company


async def upsert_source(session: AsyncSession, data: dict[str, Any]) -> SourceDocument:
    source = await session.scalar(select(SourceDocument).where(SourceDocument.source_url == data["url"]))
    if source is None:
        source = SourceDocument(source_url=data["url"], content_type="text/html")
        session.add(source)
    source.title = data["title"]
    source.publisher = data.get("publisher")
    source.is_primary = data.get("is_primary", False)
    await session.flush()
    return source


async def load(seed: dict[str, Any], *, dispose: bool = True) -> None:
    await init_db()
    async with SessionLocal() as session, session.begin():
        company = await upsert_company(session, seed["company"])
        sources = {key: await upsert_source(session, s) for key, s in seed["sources"].items()}

        rows = [
            {
                "company_id": company.id,
                "metric": metric,
                "period_end": date.fromisoformat(period_end),
                "period_type": group["period_type"],
                "basis": ReportingBasis(group["basis"]),
                "value": Decimal(str(value)),
                "unit": group["unit"],
                "source_document_id": sources[group["source"]].id,
            }
            for group in seed["facts"]
            for metric, series in group["metrics"].items()
            for period_end, value in series.items()
        ]
        stmt = insert(FinancialFact).values(rows)
        await session.execute(
            stmt.on_conflict_do_update(
                index_elements=["company_id", "metric", "period_end", "period_type", "basis"],
                set_={
                    "value": stmt.excluded.value,
                    "unit": stmt.excluded.unit,
                    "source_document_id": stmt.excluded.source_document_id,
                },
            )
        )
    log.info("seed_loaded", company=company.name, sources=len(sources), facts=len(rows))
    if dispose:
        await engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python -m scripts.load_seed <seed.json>")
    configure_logging(debug=True)
    asyncio.run(load(json.loads(Path(sys.argv[1]).read_text())))
