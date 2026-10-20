"""Load peer (competitor) companies and link them to the companies they benchmark.

Usage:
    uv run python -m scripts.load_peers            # data/seeds/peers/*.json + data/seeds/peer_sets.json
"""

import asyncio
import json
from pathlib import Path

import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.core.database import SessionLocal, engine
from app.core.logging import configure_logging
from app.models import Company, CompanyPeer
from app.models.company import Coverage
from scripts.load_seed import load

log = structlog.get_logger()
SEEDS = Path("data/seeds")


async def main() -> None:
    files = sorted((SEEDS / "peers").glob("*.json"))
    seeds = [json.loads(f.read_text()) for f in files]
    for seed in seeds:
        seed["company"]["coverage"] = Coverage.PEER
        await load(seed, dispose=False)

    peer_sets: dict[str, list[str]] = json.loads((SEEDS / "peer_sets.json").read_text())
    async with SessionLocal() as session, session.begin():
        symbols = {s for subject, peers in peer_sets.items() for s in [subject, *peers]}
        companies = {
            c.nse_symbol: c
            for c in await session.scalars(select(Company).where(Company.nse_symbol.in_(symbols)))
        }
        for subject, peers in peer_sets.items():
            if subject not in companies:
                log.warning("subject_missing", symbol=subject)
                continue
            for peer in peers:
                if peer not in companies:
                    log.warning("peer_missing", subject=subject, peer=peer)
                    continue
                await session.execute(
                    insert(CompanyPeer)
                    .values(company_id=companies[subject].id, peer_company_id=companies[peer].id)
                    .on_conflict_do_nothing()
                )
            log.info("peers_linked", subject=subject, peers=len(peers))
    await engine.dispose()


if __name__ == "__main__":
    configure_logging(debug=True)
    asyncio.run(main())
