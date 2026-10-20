"""Starting AI research for an evaluation, in-process or via the arq worker."""

import uuid

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import BackgroundTasks

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.modules.research.clients import ClaudeLLM, VoyageEmbedder
from app.modules.workflow.evaluation_service import run_research


async def run_research_job(evaluation_id: uuid.UUID) -> None:
    await run_research(SessionLocal, evaluation_id, llm_factory=ClaudeLLM, embedder_factory=VoyageEmbedder)


async def start_research(evaluation_id: uuid.UUID, background: BackgroundTasks) -> None:
    settings = get_settings()
    if settings.research_execution == "queue":
        pool = await create_pool(RedisSettings.from_dsn(str(settings.redis_url)))
        await pool.enqueue_job("run_evaluation_research", str(evaluation_id))
        await pool.aclose()
    else:
        background.add_task(run_research_job, evaluation_id)
