"""Background worker (arq + Redis) for document ingestion and AI research.

Used when RESEARCH_EXECUTION=queue. Run with: uv run arq app.worker.WorkerSettings
"""

import uuid
from typing import Any, ClassVar

from arq.connections import RedisSettings

from app.core.config import get_settings
from app.modules.workflow.jobs import run_research_job


async def run_evaluation_research(ctx: dict[str, Any], evaluation_id: str) -> None:
    await run_research_job(uuid.UUID(evaluation_id))


class WorkerSettings:
    functions: ClassVar = [run_evaluation_research]
    redis_settings = RedisSettings.from_dsn(str(get_settings().redis_url))
    max_jobs = 4
    job_timeout = 3600
