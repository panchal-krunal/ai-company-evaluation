"""AI clients behind small interfaces, so pipelines can be tested with fakes and run without keys.

The LLM extracts and interprets evidence. It never computes financial figures; the financial
engine does that in code.
"""

from typing import Protocol, TypeVar

import anthropic
import structlog
from pydantic import BaseModel

from app.core.config import get_settings

log = structlog.get_logger()

T = TypeVar("T", bound=BaseModel)


class AIConfigurationError(RuntimeError):
    """A required API key is not configured."""


class ResearchRefusedError(RuntimeError):
    pass


class LLM(Protocol):
    async def structured(self, *, system: str, prompt: str, schema: type[T]) -> T: ...


class Embedder(Protocol):
    async def embed(self, texts: list[str], *, input_type: str) -> list[list[float]]: ...


class ClaudeLLM:
    def __init__(self) -> None:
        settings = get_settings()
        key = settings.anthropic_api_key.get_secret_value() if settings.anthropic_api_key else ""
        if not key:
            raise AIConfigurationError("ANTHROPIC_API_KEY is not set in backend/.env")
        self.client = anthropic.AsyncAnthropic(api_key=key)
        self.model = settings.llm_model
        self.effort = settings.llm_effort

    async def structured(self, *, system: str, prompt: str, schema: type[T]) -> T:
        async with self.client.beta.messages.stream(
            model=self.model,
            max_tokens=32000,
            # On a safety decline, re-run on Anthropic's recommended fallback model server-side.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=system,
            thinking={"type": "adaptive"},
            output_config={"effort": self.effort},
            messages=[{"role": "user", "content": prompt}],
            output_format=schema,
        ) as stream:
            response = await stream.get_final_message()
        if response.stop_reason == "refusal":  # the whole fallback chain declined
            log.warning("llm_refusal", schema=schema.__name__, request_id=response._request_id)
            raise ResearchRefusedError(f"The model declined the request ({schema.__name__})")
        if response.stop_reason == "max_tokens":
            raise ValueError(f"Output was cut off at max_tokens ({schema.__name__})")
        parsed = response.parsed_output
        if not isinstance(parsed, schema):
            raise ValueError(f"No structured output returned (stop_reason={response.stop_reason})")
        return parsed


class VoyageEmbedder:
    batch_size = 64

    def __init__(self) -> None:
        from voyageai.client_async import AsyncClient

        settings = get_settings()
        key = settings.voyage_api_key.get_secret_value() if settings.voyage_api_key else ""
        if not key:
            raise AIConfigurationError("VOYAGE_API_KEY is not set in backend/.env")
        self.client = AsyncClient(api_key=key, max_retries=3)
        self.model = settings.embedding_model
        self.dimensions = settings.embedding_dimensions

    async def embed(self, texts: list[str], *, input_type: str) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            result = await self.client.embed(
                texts[start : start + self.batch_size],
                model=self.model,
                input_type=input_type,
                output_dimension=self.dimensions,
            )
            vectors.extend([float(x) for x in v] for v in result.embeddings)
        return vectors


def ai_capabilities() -> dict[str, bool]:
    settings = get_settings()
    return {
        "llm": bool(settings.anthropic_api_key and settings.anthropic_api_key.get_secret_value()),
        "embeddings": bool(settings.voyage_api_key and settings.voyage_api_key.get_secret_value()),
    }
