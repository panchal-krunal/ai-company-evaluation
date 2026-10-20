import enum
import uuid
from typing import Any

from sqlalchemy import JSON, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin


class EvaluationStatus(enum.StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"


class Evaluation(IdMixin, TimestampMixin, Base):
    __tablename__ = "evaluations"

    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    status: Mapped[EvaluationStatus] = mapped_column(Enum(EvaluationStatus), default=EvaluationStatus.DRAFT)
    formula_version: Mapped[str] = mapped_column(String(32))
    prompt_version: Mapped[str] = mapped_column(String(32))
    approved_by: Mapped[str | None] = mapped_column(String(255))

    findings: Mapped[list[ModuleFinding]] = relationship(back_populates="evaluation")


class FindingStatus(enum.StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"  # rule-based part done; the AI part has not run yet
    QUEUED = "queued"
    RUNNING = "running"
    FAILED = "failed"
    NOT_RUN = "not_run"  # missing data or configuration; `error` says why


class ModuleFinding(IdMixin, TimestampMixin, Base):
    """The system's output for one of the ten modules, plus any analyst override."""

    __tablename__ = "module_findings"
    __table_args__ = (UniqueConstraint("evaluation_id", "module"),)

    evaluation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evaluations.id"), index=True)
    module: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default=FindingStatus.COMPLETE, server_default="complete")
    error: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    override_summary: Mapped[str | None] = mapped_column(Text)
    override_reason: Mapped[str | None] = mapped_column(Text)

    evaluation: Mapped[Evaluation] = relationship(back_populates="findings")


class AnalystComment(IdMixin, TimestampMixin, Base):
    __tablename__ = "analyst_comments"

    finding_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("module_findings.id"), index=True)
    author: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)


class AuditEvent(IdMixin, TimestampMixin, Base):
    """Append-only audit trail of analyst and system actions."""

    __tablename__ = "audit_events"

    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[uuid.UUID] = mapped_column(index=True)
    action: Mapped[str] = mapped_column(String(64))
    actor: Mapped[str] = mapped_column(String(255))
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
