"""Run a full evaluation (rule-based + AI modules) for one or all companies, from the terminal.

Usage (after ANTHROPIC_API_KEY and VOYAGE_API_KEY are set and documents are ingested):
    uv run python -m scripts.run_research --symbol CUPID
    uv run python -m scripts.run_research --all
    uv run python -m scripts.run_research --evaluation <evaluation-id>   # re-run AI modules only
"""

import argparse
import asyncio
import uuid

import structlog
from sqlalchemy import select

from app.core.database import SessionLocal, engine, init_db
from app.core.logging import configure_logging
from app.models import Company
from app.models.company import Coverage
from app.modules.research.clients import ClaudeLLM, VoyageEmbedder
from app.modules.workflow.evaluation_service import (
    create_evaluation,
    get_evaluation,
    queue_research,
    research_blockers,
    run_research,
)

log = structlog.get_logger()


async def run_for(evaluation_id: uuid.UUID) -> None:
    await run_research(SessionLocal, evaluation_id, llm_factory=ClaudeLLM, embedder_factory=VoyageEmbedder)
    async with SessionLocal() as session:
        evaluation = await get_evaluation(session, evaluation_id)
        for f in sorted(evaluation.findings if evaluation else [], key=lambda f: f.module):
            log.info("module", module=f.module, status=f.status, error=f.error)


async def main(args: argparse.Namespace) -> None:
    await init_db()
    if args.evaluation:
        async with SessionLocal() as session:
            evaluation = await get_evaluation(session, uuid.UUID(args.evaluation))
            if evaluation is None:
                raise SystemExit("Evaluation not found")
            if blockers := await queue_research(session, evaluation, "cli"):
                raise SystemExit("Cannot run AI modules: " + "; ".join(blockers))
        await run_for(uuid.UUID(args.evaluation))
    else:
        async with SessionLocal() as session:
            stmt = select(Company).where(Company.coverage == Coverage.EVALUATED)
            if args.symbol:
                stmt = stmt.where(Company.nse_symbol == args.symbol)
            companies = list(await session.scalars(stmt))
        for company in companies:
            async with SessionLocal() as session:
                if blockers := await research_blockers(session, company.id):
                    log.warning("ai_modules_blocked", company=company.name, blockers=blockers)
                evaluation = await create_evaluation(session, company, actor="cli")
                evaluation_id = evaluation.id
            log.info("evaluation_created", company=company.name, evaluation_id=str(evaluation_id))
            await run_for(evaluation_id)
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--symbol")
    group.add_argument("--all", action="store_true")
    group.add_argument("--evaluation")
    configure_logging(debug=True)
    asyncio.run(main(parser.parse_args()))
