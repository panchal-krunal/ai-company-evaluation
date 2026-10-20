import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.evaluation import EvaluationStatus


class GrowthYearRead(BaseModel):
    period_end: date
    revenue: float | None
    revenue_growth: float | None
    gross_margin: float | None
    ebitda_margin: float | None
    net_margin: float | None


class GrowthReport(BaseModel):
    years: list[GrowthYearRead]
    revenue_cagr_3y: float | None
    revenue_cagr_full: float | None
    full_period_years: int
    source_document_ids: list[str]


class FindingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    module: str
    status: str
    error: str | None
    summary: str
    data: dict[str, Any]
    evidence: list[dict[str, Any]]
    override_summary: str | None
    override_reason: str | None


class EvaluationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    status: EvaluationStatus
    formula_version: str
    created_at: datetime


class EvaluationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    status: EvaluationStatus
    formula_version: str
    prompt_version: str
    approved_by: str | None
    created_at: datetime
    findings: list[FindingRead]


class ActorBody(BaseModel):
    actor: str = Field(
        min_length=1, max_length=255, description="Analyst name (authentication is added later)"
    )


class ReturnBody(ActorBody):
    reason: str = Field(min_length=3)


class CommentCreate(BaseModel):
    author: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1, max_length=10_000)


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    finding_id: uuid.UUID
    author: str
    body: str
    created_at: datetime


class OverrideBody(ActorBody):
    summary: str | None = Field(description="Analyst's replacement conclusion; null removes the override")
    reason: str | None = None


class AuditEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    action: str
    actor: str
    details: dict[str, Any]
    created_at: datetime


class ResearchQueued(BaseModel):
    queued: bool
    blockers: list[str]
