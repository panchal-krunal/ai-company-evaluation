from collections.abc import AsyncIterator

import structlog
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.models import Base

log = structlog.get_logger()

engine = create_async_engine(str(get_settings().database_url), pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    """Enable pgvector and create any tables defined in `app.models` that don't exist yet.

    `create_all` only creates missing tables; it never alters existing ones (new columns,
    type changes). Use Alembic migrations for schema changes, and in UAT/production.
    """
    async with engine.begin() as conn:
        has_vector = await conn.scalar(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'"))
        if not has_vector:
            try:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            except DBAPIError as exc:
                db = engine.url.database
                raise RuntimeError(
                    f"The pgvector extension is not enabled in database '{db}', and user "
                    f"'{engine.url.username}' is not allowed to enable it. Run once as a "
                    f'Postgres superuser:\n  psql -p {engine.url.port} -d {db} -c "CREATE EXTENSION vector;"'
                ) from exc
        await conn.run_sync(Base.metadata.create_all)
    log.info("database_initialised", tables=sorted(Base.metadata.tables))
