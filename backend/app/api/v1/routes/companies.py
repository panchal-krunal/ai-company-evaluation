import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models import Company, CompanyPeer, Evaluation, FinancialFact, SourceDocument
from app.models.company import Coverage, ReportingBasis
from app.schemas.company import CompanyCreate, CompanyRead
from app.schemas.evaluation import EvaluationSummary
from app.schemas.financials import FinancialFactRead, SourceDocumentRead

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=list[CompanyRead])
async def list_companies(
    session: AsyncSession = Depends(get_session),
    include_peers: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> list[Company]:
    """Companies under evaluation. Peer-only benchmark companies are hidden unless include_peers=true."""
    stmt = select(Company).order_by(Company.name).limit(limit).offset(offset)
    if not include_peers:
        stmt = stmt.where(Company.coverage == Coverage.EVALUATED)
    return list(await session.scalars(stmt))


@router.post("", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
async def create_company(payload: CompanyCreate, session: AsyncSession = Depends(get_session)) -> Company:
    company = Company(**payload.model_dump())
    session.add(company)
    await session.commit()
    await session.refresh(company)
    return company


@router.get("/{company_id}", response_model=CompanyRead)
async def get_company(company_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> Company:
    company = await session.get(Company, company_id)
    if company is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found")
    return company


@router.get("/{company_id}/financials", response_model=list[FinancialFactRead])
async def company_financials(
    company_id: uuid.UUID,
    basis: ReportingBasis = ReportingBasis.CONSOLIDATED,
    period_type: Literal["FY", "Q"] | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[FinancialFact]:
    """Normalised figures for the company, ordered by metric then period."""
    await get_company(company_id, session)
    stmt = select(FinancialFact).where(FinancialFact.company_id == company_id, FinancialFact.basis == basis)
    if period_type:
        stmt = stmt.where(FinancialFact.period_type == period_type)
    return list(await session.scalars(stmt.order_by(FinancialFact.metric, FinancialFact.period_end)))


@router.get("/{company_id}/sources", response_model=list[SourceDocumentRead])
async def company_sources(
    company_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> list[SourceDocument]:
    """Source documents that this company's figures are traced to."""
    await get_company(company_id, session)
    used = select(FinancialFact.source_document_id).where(FinancialFact.company_id == company_id)
    return list(
        await session.scalars(
            select(SourceDocument).where(SourceDocument.id.in_(used)).order_by(SourceDocument.title)
        )
    )


@router.get("/{company_id}/evaluations", response_model=list[EvaluationSummary])
async def company_evaluations(
    company_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> list[Evaluation]:
    await get_company(company_id, session)
    stmt = (
        select(Evaluation).where(Evaluation.company_id == company_id).order_by(Evaluation.created_at.desc())
    )
    return list(await session.scalars(stmt))


@router.get("/{company_id}/peers", response_model=list[CompanyRead])
async def company_peers(company_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> list[Company]:
    await get_company(company_id, session)
    stmt = (
        select(Company)
        .join(CompanyPeer, CompanyPeer.peer_company_id == Company.id)
        .where(CompanyPeer.company_id == company_id)
        .order_by(Company.name)
    )
    return list(await session.scalars(stmt))
