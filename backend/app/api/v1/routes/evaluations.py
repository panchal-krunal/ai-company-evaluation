import uuid
from dataclasses import asdict

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.models import AnalystComment, Company, Evaluation, ModuleFinding
from app.models.company import ReportingBasis
from app.modules.financial_engine.company_analysis import analyse_growth, evaluate_warnings, load_facts
from app.modules.reporting.export import to_json, to_markdown
from app.modules.workflow import actions
from app.modules.workflow.evaluation_service import (
    EvaluationLockedError,
    create_evaluation,
    get_evaluation,
    queue_research,
)
from app.modules.workflow.jobs import start_research
from app.schemas.evaluation import (
    ActorBody,
    AuditEventRead,
    CommentCreate,
    CommentRead,
    EvaluationRead,
    FindingRead,
    GrowthReport,
    GrowthYearRead,
    OverrideBody,
    ResearchQueued,
    ReturnBody,
)
from app.schemas.warnings import WarningReport, WarningResultRead

router = APIRouter(tags=["evaluations"])


async def _company(session: AsyncSession, company_id: uuid.UUID) -> Company:
    company = await session.get(Company, company_id)
    if company is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found")
    return company


async def _evaluation(session: AsyncSession, evaluation_id: uuid.UUID) -> Evaluation:
    evaluation = await get_evaluation(session, evaluation_id)
    if evaluation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evaluation not found")
    return evaluation


async def _finding(session: AsyncSession, finding_id: uuid.UUID) -> tuple[Evaluation, ModuleFinding]:
    finding = await session.get(ModuleFinding, finding_id)
    if finding is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Finding not found")
    return await _evaluation(session, finding.evaluation_id), finding


def _conflict(exc: Exception) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, str(exc))


@router.get("/companies/{company_id}/warnings", response_model=WarningReport)
async def company_warnings(
    company_id: uuid.UUID,
    basis: ReportingBasis = ReportingBasis.CONSOLIDATED,
    session: AsyncSession = Depends(get_session),
) -> WarningReport:
    """Run the eight warning checks on the company's stored figures (latest fiscal year)."""
    await _company(session, company_id)
    fy = await load_facts(session, company_id, basis, "FY")
    quarterly = await load_facts(session, company_id, basis, "Q")
    try:
        as_of, results = evaluate_warnings(fy, quarterly, review_years=get_settings().warning_review_years)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return WarningReport(
        formula_version=get_settings().formula_version,
        as_of=as_of,
        results=[WarningResultRead(**asdict(r)) for r in results],
    )


@router.get("/companies/{company_id}/growth", response_model=GrowthReport)
async def company_growth(
    company_id: uuid.UUID,
    basis: ReportingBasis = ReportingBasis.CONSOLIDATED,
    session: AsyncSession = Depends(get_session),
) -> GrowthReport:
    await _company(session, company_id)
    g = analyse_growth(await load_facts(session, company_id, basis, "FY"))
    return GrowthReport(
        years=[GrowthYearRead(**asdict(y)) for y in g.years],
        revenue_cagr_3y=g.revenue_cagr_3y,
        revenue_cagr_full=g.revenue_cagr_full,
        full_period_years=g.full_period_years,
        source_document_ids=list(g.source_document_ids),
    )


@router.post(
    "/companies/{company_id}/evaluations", response_model=EvaluationRead, status_code=status.HTTP_201_CREATED
)
async def start_evaluation(
    company_id: uuid.UUID,
    background: BackgroundTasks,
    body: ActorBody | None = None,
    session: AsyncSession = Depends(get_session),
) -> Evaluation:
    """Create a draft evaluation: rule-based modules run now, AI modules start in the background."""
    company = await _company(session, company_id)
    try:
        evaluation = await create_evaluation(session, company, actor=body.actor if body else "system")
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    if any(f.status == "queued" for f in evaluation.findings):
        await start_research(evaluation.id, background)
    return evaluation


@router.get("/evaluations/{evaluation_id}", response_model=EvaluationRead)
async def read_evaluation(
    evaluation_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> Evaluation:
    return await _evaluation(session, evaluation_id)


@router.post("/evaluations/{evaluation_id}/research", response_model=ResearchQueued)
async def rerun_research(
    evaluation_id: uuid.UUID,
    body: ActorBody,
    background: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> ResearchQueued:
    """(Re)run the AI modules. Returns what blocks them when keys or documents are missing."""
    evaluation = await _evaluation(session, evaluation_id)
    try:
        blockers = await queue_research(session, evaluation, body.actor)
    except EvaluationLockedError as exc:
        raise _conflict(exc) from exc
    if not blockers:
        await start_research(evaluation_id, background)
    return ResearchQueued(queued=not blockers, blockers=blockers)


@router.post("/evaluations/{evaluation_id}/submit", response_model=EvaluationRead)
async def submit(
    evaluation_id: uuid.UUID, body: ActorBody, session: AsyncSession = Depends(get_session)
) -> Evaluation:
    evaluation = await _evaluation(session, evaluation_id)
    try:
        await actions.submit_for_review(session, evaluation, body.actor)
    except actions.WorkflowError as exc:
        raise _conflict(exc) from exc
    return await _evaluation(session, evaluation_id)


@router.post("/evaluations/{evaluation_id}/approve", response_model=EvaluationRead)
async def approve(
    evaluation_id: uuid.UUID, body: ActorBody, session: AsyncSession = Depends(get_session)
) -> Evaluation:
    evaluation = await _evaluation(session, evaluation_id)
    try:
        await actions.approve(session, evaluation, body.actor)
    except actions.WorkflowError as exc:
        raise _conflict(exc) from exc
    return await _evaluation(session, evaluation_id)


@router.post("/evaluations/{evaluation_id}/return", response_model=EvaluationRead)
async def return_to_draft(
    evaluation_id: uuid.UUID, body: ReturnBody, session: AsyncSession = Depends(get_session)
) -> Evaluation:
    evaluation = await _evaluation(session, evaluation_id)
    try:
        await actions.return_to_draft(session, evaluation, body.actor, body.reason)
    except actions.WorkflowError as exc:
        raise _conflict(exc) from exc
    return await _evaluation(session, evaluation_id)


@router.get("/evaluations/{evaluation_id}/audit", response_model=list[AuditEventRead])
async def audit(evaluation_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> list[object]:
    return list(await actions.audit_trail(session, await _evaluation(session, evaluation_id)))


@router.get("/evaluations/{evaluation_id}/export")
async def export(
    evaluation_id: uuid.UUID, format: str = "markdown", session: AsyncSession = Depends(get_session)
) -> Response:
    evaluation = await _evaluation(session, evaluation_id)
    company = await _company(session, evaluation.company_id)
    stem = f"{company.nse_symbol or 'company'}_evaluation_{evaluation.created_at:%Y%m%d}"
    if format == "json":
        import json

        return Response(
            json.dumps(to_json(evaluation, company), indent=2, default=str),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{stem}.json"'},
        )
    return Response(
        to_markdown(evaluation, company),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{stem}.md"'},
    )


@router.get("/findings/{finding_id}/comments", response_model=list[CommentRead])
async def list_comments(
    finding_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> list[AnalystComment]:
    await _finding(session, finding_id)
    stmt = (
        select(AnalystComment)
        .where(AnalystComment.finding_id == finding_id)
        .order_by(AnalystComment.created_at)
    )
    return list(await session.scalars(stmt))


@router.post(
    "/findings/{finding_id}/comments", response_model=CommentRead, status_code=status.HTTP_201_CREATED
)
async def add_comment(
    finding_id: uuid.UUID, body: CommentCreate, session: AsyncSession = Depends(get_session)
) -> AnalystComment:
    _, finding = await _finding(session, finding_id)
    return await actions.add_comment(session, finding, body.author, body.body)


@router.put("/findings/{finding_id}/override", response_model=FindingRead)
async def override(
    finding_id: uuid.UUID, body: OverrideBody, session: AsyncSession = Depends(get_session)
) -> ModuleFinding:
    evaluation, finding = await _finding(session, finding_id)
    try:
        return await actions.set_override(session, evaluation, finding, body.actor, body.summary, body.reason)
    except actions.WorkflowError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
