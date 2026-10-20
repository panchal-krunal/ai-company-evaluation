"""Analyst actions on an evaluation. Every action writes an audit event."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AnalystComment, AuditEvent, Evaluation, ModuleFinding
from app.models.evaluation import EvaluationStatus, FindingStatus


class WorkflowError(ValueError):
    pass


def _audit(
    session: AsyncSession, entity_type: str, entity_id: uuid.UUID, action: str, actor: str, **details: object
) -> None:
    session.add(
        AuditEvent(entity_type=entity_type, entity_id=entity_id, action=action, actor=actor, details=details)
    )


async def add_comment(
    session: AsyncSession, finding: ModuleFinding, author: str, body: str
) -> AnalystComment:
    comment = AnalystComment(finding_id=finding.id, author=author, body=body)
    session.add(comment)
    await session.flush()
    _audit(
        session, "finding", finding.id, "commented", author, module=finding.module, comment_id=str(comment.id)
    )
    await session.commit()
    await session.refresh(comment)
    return comment


async def set_override(
    session: AsyncSession,
    evaluation: Evaluation,
    finding: ModuleFinding,
    actor: str,
    summary: str | None,
    reason: str | None,
) -> ModuleFinding:
    if evaluation.status == EvaluationStatus.APPROVED:
        raise WorkflowError("Approved evaluations are locked")
    if summary is not None and not (reason and reason.strip()):
        raise WorkflowError("A reason is required to override a finding")
    previous = finding.override_summary
    finding.override_summary = summary
    finding.override_reason = reason if summary is not None else None
    _audit(
        session,
        "finding",
        finding.id,
        "overridden" if summary is not None else "override_removed",
        actor,
        module=finding.module,
        previous=previous,
        summary=summary,
        reason=reason,
    )
    await session.commit()
    return finding


async def submit_for_review(session: AsyncSession, evaluation: Evaluation, actor: str) -> Evaluation:
    if evaluation.status != EvaluationStatus.DRAFT:
        raise WorkflowError(f"Only draft evaluations can be submitted (status is {evaluation.status})")
    evaluation.status = EvaluationStatus.IN_REVIEW
    _audit(session, "evaluation", evaluation.id, "submitted_for_review", actor)
    await session.commit()
    return evaluation


async def approve(session: AsyncSession, evaluation: Evaluation, actor: str) -> Evaluation:
    if evaluation.status != EvaluationStatus.IN_REVIEW:
        raise WorkflowError(f"Only evaluations in review can be approved (status is {evaluation.status})")
    busy = await session.scalar(
        select(ModuleFinding.module).where(
            ModuleFinding.evaluation_id == evaluation.id,
            ModuleFinding.status.in_([FindingStatus.QUEUED, FindingStatus.RUNNING]),
        )
    )
    if busy:
        raise WorkflowError(f"Wait for the {busy} module to finish before approving")
    evaluation.status = EvaluationStatus.APPROVED
    evaluation.approved_by = actor
    _audit(session, "evaluation", evaluation.id, "approved", actor, approved_at=datetime.now(UTC).isoformat())
    await session.commit()
    return evaluation


async def return_to_draft(
    session: AsyncSession, evaluation: Evaluation, actor: str, reason: str
) -> Evaluation:
    if evaluation.status != EvaluationStatus.IN_REVIEW:
        raise WorkflowError("Only evaluations in review can be returned to draft")
    evaluation.status = EvaluationStatus.DRAFT
    _audit(session, "evaluation", evaluation.id, "returned_to_draft", actor, reason=reason)
    await session.commit()
    return evaluation


async def audit_trail(session: AsyncSession, evaluation: Evaluation) -> list[AuditEvent]:
    finding_ids = [f.id for f in evaluation.findings]
    return list(
        await session.scalars(
            select(AuditEvent)
            .where(AuditEvent.entity_id.in_([evaluation.id, *finding_ids]))
            .order_by(AuditEvent.created_at)
        )
    )
