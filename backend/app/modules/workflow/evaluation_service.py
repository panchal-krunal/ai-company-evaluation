"""Build and run an evaluation across the ten modules.

Rule-based modules (financial warnings, growth, competitors, debt metrics, the Why Not Invest draft)
run synchronously when the evaluation is created. AI modules run afterwards in `run_research`,
one at a time, committing progress so the dashboard can show each module's status.
"""

import uuid
from collections.abc import Callable
from dataclasses import asdict
from datetime import date
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models import (
    AuditEvent,
    Company,
    CompanyPeer,
    Evaluation,
    FinancialFact,
    ModuleFinding,
    SourceDocument,
)
from app.models.company import ReportingBasis
from app.models.evaluation import EvaluationStatus, FindingStatus
from app.modules.financial_engine.company_analysis import (
    FactTable,
    GrowthAnalysis,
    analyse_growth,
    evaluate_warnings,
    load_facts,
)
from app.modules.financial_engine.debt import DebtYear, debt_profile
from app.modules.financial_engine.peers import METRICS, CompanyRow, compare, latest_metrics
from app.modules.financial_engine.red_flags import draft_red_flags
from app.modules.financial_engine.warnings import WarningResult, WarningStatus
from app.modules.research.clients import LLM, AIConfigurationError, Embedder, ai_capabilities
from app.modules.research.prompts import RESEARCH_SPECS
from app.modules.research.retrieval import count_embedded_chunks
from app.modules.research.runner import (
    NoPassagesError,
    run_debt_extraction,
    run_research_module,
    run_rpt_extraction,
    run_why_not_invest,
)

log = structlog.get_logger()

RULE_MODULES = ["financial_warnings", "growth_analysis", "competitors", "debt_structure"]
AI_ONLY_MODULES = ["related_party_transactions", *RESEARCH_SPECS]
ALL_MODULES = [*RULE_MODULES, *AI_ONLY_MODULES, "why_not_invest"]


class EvaluationLockedError(RuntimeError):
    pass


def fiscal_year(period_end: date) -> str:
    """Indian fiscal years end on 31 March: 2026-03-31 is FY2026."""
    return f"FY{period_end.year if period_end.month <= 3 else period_end.year + 1}"


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def _x(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}×"


def summarise_warnings(results: list[WarningResult], as_of: date) -> str:
    by_status: dict[WarningStatus, list[str]] = {s: [] for s in WarningStatus}
    for r in results:
        by_status[r.status].append(r.check.value.replace("_", " "))
    assessed = len(results) - len(by_status[WarningStatus.NOT_ASSESSED])
    parts = [f"{fiscal_year(as_of)}: {assessed} of {len(results)} checks assessed."]
    for status in (WarningStatus.FLAG, WarningStatus.WATCH, WarningStatus.CLEAR, WarningStatus.NOT_ASSESSED):
        if by_status[status]:
            parts.append(f"{status.value.replace('_', ' ').capitalize()}: {', '.join(by_status[status])}.")
    return " ".join(parts)


def summarise_growth(g: GrowthAnalysis) -> str:
    if not g.years:
        return "No annual revenue data."
    first, last = g.years[0], g.years[-1]
    return (
        f"Revenue grew from ₹{first.revenue or 0:,.1f} Cr ({fiscal_year(first.period_end)}) to "
        f"₹{last.revenue or 0:,.1f} Cr ({fiscal_year(last.period_end)}): {g.full_period_years}-year CAGR "
        f"{_pct(g.revenue_cagr_full)}, 3-year CAGR {_pct(g.revenue_cagr_3y)}, latest year "
        f"{_pct(last.revenue_growth)}. Net margin moved from {_pct(first.net_margin)} to "
        f"{_pct(last.net_margin)}; gross margin from {_pct(first.gross_margin)} to {_pct(last.gross_margin)}."
    )


def summarise_debt(years: list[DebtYear]) -> str:
    if not years:
        return "No debt figures stored."
    d = years[-1]
    if d.net_debt is None:
        net = "net debt n/a"
    elif d.net_debt < 0:
        net = f"net cash ₹{-d.net_debt:,.1f} Cr"
    else:
        net = f"net debt ₹{d.net_debt:,.1f} Cr"
    if d.interest_coverage is None:
        cover = "interest cover n/a"
    elif d.interest_coverage < 0:
        cover = "operating loss, so interest is not covered by EBIT"
    else:
        cover = f"interest cover {_x(d.interest_coverage)}"
    return (
        f"{fiscal_year(d.period_end)}: total debt ₹{d.total_debt or 0:,.1f} Cr, {net}; debt/equity "
        f"{_x(d.debt_to_equity)}, debt/EBITDA {_x(d.debt_to_ebitda)}, {cover}, implied interest rate "
        f"{_pct(d.implied_interest_rate)}, short-term share {_pct(d.short_term_share)}."
    )


async def _evidence(session: AsyncSession, ids: set[str]) -> list[dict[str, Any]]:
    if not ids:
        return []
    docs = await session.scalars(
        select(SourceDocument).where(SourceDocument.id.in_([uuid.UUID(i) for i in ids]))
    )
    return [
        {
            "source_document_id": str(d.id),
            "title": d.title,
            "url": d.source_url,
            "publisher": d.publisher,
            "is_primary": d.is_primary,
            "doc_type": d.doc_type,
        }
        for d in docs
    ]


def _iso(value: Any) -> Any:
    return value.isoformat() if isinstance(value, date) else value


async def _set(
    session: AsyncSession,
    evaluation_id: uuid.UUID,
    module: str,
    *,
    status: str,
    summary: str = "",
    data: dict[str, Any] | None = None,
    evidence: list[dict[str, Any]] | None = None,
    error: str | None = None,
) -> ModuleFinding:
    finding = await session.scalar(
        select(ModuleFinding).where(
            ModuleFinding.evaluation_id == evaluation_id, ModuleFinding.module == module
        )
    )
    if finding is None:
        finding = ModuleFinding(evaluation_id=evaluation_id, module=module, summary="", data={}, evidence=[])
        session.add(finding)
    finding.status = status
    finding.summary = summary
    finding.error = error
    if data is not None:
        finding.data = data
    if evidence is not None:
        finding.evidence = evidence
    await session.flush()
    return finding


# ---------- rule-based modules ----------


async def _warnings_finding(session: AsyncSession, evaluation_id: uuid.UUID, company_id: uuid.UUID) -> None:
    settings = get_settings()
    fy = await load_facts(session, company_id, ReportingBasis.CONSOLIDATED, "FY")
    quarterly = await load_facts(session, company_id, ReportingBasis.CONSOLIDATED, "Q")
    as_of, warnings = evaluate_warnings(fy, quarterly, review_years=settings.warning_review_years)
    await _set(
        session,
        evaluation_id,
        "financial_warnings",
        status=FindingStatus.COMPLETE,
        summary=summarise_warnings(warnings, as_of),
        data={
            "as_of": as_of.isoformat(),
            "basis": "consolidated",
            "results": [{**asdict(r), "source_document_ids": list(r.source_document_ids)} for r in warnings],
        },
        evidence=await _evidence(session, {i for r in warnings for i in r.source_document_ids}),
    )


async def _competitor_rows(
    session: AsyncSession, company: Company, fy: FactTable
) -> tuple[CompanyRow, list[CompanyRow]]:
    def row(c: Company, table: FactTable, is_subject: bool) -> CompanyRow:
        period, values = latest_metrics(table)
        sources = table.source_ids(
            ["revenue", "net_profit", "total_debt", "equity"], [period] if period else []
        )
        return CompanyRow(str(c.id), c.name, c.nse_symbol, is_subject, period, values, sources)

    peers = list(
        await session.scalars(
            select(Company)
            .join(CompanyPeer, CompanyPeer.peer_company_id == Company.id)
            .where(CompanyPeer.company_id == company.id)
            .order_by(Company.name)
        )
    )
    peer_rows = [
        row(p, await load_facts(session, p.id, ReportingBasis.CONSOLIDATED, "FY"), False) for p in peers
    ]
    return row(company, fy, True), peer_rows


async def _rule_based_findings(session: AsyncSession, evaluation: Evaluation, company: Company) -> None:
    eid = evaluation.id
    fy = await load_facts(session, company.id, ReportingBasis.CONSOLIDATED, "FY")
    await _warnings_finding(session, eid, company.id)

    growth = analyse_growth(fy)
    await _set(
        session,
        eid,
        "growth_analysis",
        status=FindingStatus.COMPLETE,
        summary=summarise_growth(growth),
        data={
            "basis": "consolidated",
            "revenue_cagr_3y": growth.revenue_cagr_3y,
            "revenue_cagr_full": growth.revenue_cagr_full,
            "full_period_years": growth.full_period_years,
            "years": [{**asdict(y), "period_end": y.period_end.isoformat()} for y in growth.years],
        },
        evidence=await _evidence(session, set(growth.source_document_ids)),
    )

    subject, peers = await _competitor_rows(session, company, fy)
    if peers:
        comparison = compare(subject, peers)
        metrics: list[dict[str, Any]] = [
            {
                "key": key,
                "label": label,
                "higher_is_better": higher,
                "subject": subject.values.get(key),
                "peer_median": comparison.peer_median[key],
                "rank": comparison.subject_rank[key],
                "better_than_median": comparison.better_than_median[key],
            }
            for key, label, higher in METRICS
        ]
        better = [m["label"] for m in metrics if m["better_than_median"] is True and m["key"] != "revenue"]
        worse = [m["label"] for m in metrics if m["better_than_median"] is False and m["key"] != "revenue"]
        await _set(
            session,
            eid,
            "competitors",
            status=FindingStatus.COMPLETE,
            summary=(
                f"Compared with {len(peers)} listed peers on the latest fiscal year. Better than the peer median "
                f"on: {', '.join(better) or 'none'}. Worse on: {', '.join(worse) or 'none'}."
            ),
            data={
                "metrics": metrics,
                "companies": [
                    {
                        **asdict(r),
                        "period_end": _iso(r.period_end),
                        "source_document_ids": list(r.source_document_ids),
                    }
                    for r in comparison.rows
                ],
            },
            evidence=await _evidence(session, {i for r in comparison.rows for i in r.source_document_ids}),
        )
    else:
        await _set(
            session, eid, "competitors", status=FindingStatus.NOT_RUN, error="No peer companies defined."
        )

    years = debt_profile(fy)
    debt_sources = fy.source_ids(
        ["total_debt", "equity", "ebitda", "ebit", "interest_expense"], fy.periods("total_debt")
    )
    await _set(
        session,
        eid,
        "debt_structure",
        status=FindingStatus.PARTIAL,
        summary=summarise_debt(years),
        data={
            "years": [{**asdict(y), "period_end": y.period_end.isoformat()} for y in years],
            "borrowings": None,
        },
        evidence=await _evidence(session, set(debt_sources)),
        error="Borrowing-level detail (lenders, rates, security) comes from the AI extraction step.",
    )


async def _why_not_invest_draft(
    session: AsyncSession, evaluation_id: uuid.UUID, ai_narrative: dict[str, Any] | None
) -> None:
    findings = {
        f.module: {"summary": f.summary, **f.data}
        for f in await session.scalars(
            select(ModuleFinding).where(ModuleFinding.evaluation_id == evaluation_id)
        )
        if f.module != "why_not_invest"
    }
    flags = draft_red_flags(findings)
    data: dict[str, Any] = {"rule_based_flags": [asdict(f) for f in flags], "ai": ai_narrative}
    high = sum(1 for f in flags if f.severity == "high")
    summary = (
        ai_narrative["summary"]
        if ai_narrative
        else f"Rule-based draft: {len(flags)} concerns ({high} high severity) from the financial modules."
    )
    await _set(
        session,
        evaluation_id,
        "why_not_invest",
        status=FindingStatus.COMPLETE if ai_narrative else FindingStatus.PARTIAL,
        summary=summary,
        data=data,
        error=None if ai_narrative else "AI narrative not generated yet; showing rule-based concerns only.",
    )


# ---------- lifecycle ----------


async def research_blockers(session: AsyncSession, company_id: uuid.UUID) -> list[str]:
    caps = ai_capabilities()
    blockers = []
    if not caps["llm"]:
        blockers.append("ANTHROPIC_API_KEY is not set in backend/.env")
    if not caps["embeddings"]:
        blockers.append("VOYAGE_API_KEY is not set in backend/.env")
    if caps["embeddings"] and not await count_embedded_chunks(session, company_id):
        blockers.append("No embedded documents for this company (run scripts.ingest_documents)")
    return blockers


async def create_evaluation(session: AsyncSession, company: Company, actor: str = "system") -> Evaluation:
    settings = get_settings()
    evaluation = Evaluation(
        company_id=company.id,
        formula_version=settings.formula_version,
        prompt_version=settings.prompt_version,
    )
    session.add(evaluation)
    await session.flush()
    await _rule_based_findings(session, evaluation, company)

    blockers = await research_blockers(session, company.id)
    for module in AI_ONLY_MODULES:
        await _set(
            session,
            evaluation.id,
            module,
            status=FindingStatus.NOT_RUN if blockers else FindingStatus.QUEUED,
            error="; ".join(blockers) or None,
        )
    await _why_not_invest_draft(session, evaluation.id, None)
    session.add(
        AuditEvent(
            entity_type="evaluation",
            entity_id=evaluation.id,
            action="created",
            actor=actor,
            details={"company_id": str(company.id), "formula_version": settings.formula_version},
        )
    )
    await session.commit()
    return await get_evaluation(session, evaluation.id)  # type: ignore[return-value]


async def queue_research(session: AsyncSession, evaluation: Evaluation, actor: str) -> list[str]:
    """Mark AI modules queued. Returns blockers (empty list = OK to run)."""
    if evaluation.status == EvaluationStatus.APPROVED:
        raise EvaluationLockedError("Approved evaluations are locked")
    blockers = await research_blockers(session, evaluation.company_id)
    if blockers:
        return blockers
    for module in [*AI_ONLY_MODULES, "debt_structure", "why_not_invest"]:
        finding = await session.scalar(
            select(ModuleFinding).where(
                ModuleFinding.evaluation_id == evaluation.id, ModuleFinding.module == module
            )
        )
        if finding and module in AI_ONLY_MODULES:
            finding.status, finding.error = FindingStatus.QUEUED, None
    session.add(
        AuditEvent(
            entity_type="evaluation",
            entity_id=evaluation.id,
            action="research_queued",
            actor=actor,
            details={},
        )
    )
    await session.commit()
    return []


async def _store_rpt_fact(
    session: AsyncSession, company_id: uuid.UUID, total_cr: float, source_ids: set[str]
) -> None:
    """Persist the extracted RPT total as a financial fact so the RPT warning check can run."""
    fy = await load_facts(session, company_id, ReportingBasis.CONSOLIDATED, "FY")
    years = fy.periods("revenue")
    if not years:
        return
    stmt = insert(FinancialFact).values(
        company_id=company_id,
        metric="rpt_value",
        period_end=years[-1],
        period_type="FY",
        basis=ReportingBasis.CONSOLIDATED,
        value=Decimal(str(round(total_cr, 4))),
        unit="INR_CR",
        source_document_id=uuid.UUID(sorted(source_ids)[0]) if source_ids else None,
    )
    await session.execute(
        stmt.on_conflict_do_update(
            index_elements=["company_id", "metric", "period_end", "period_type", "basis"],
            set_={"value": stmt.excluded.value, "source_document_id": stmt.excluded.source_document_id},
        )
    )


async def run_research(
    session_factory: async_sessionmaker[AsyncSession],
    evaluation_id: uuid.UUID,
    *,
    llm_factory: Callable[[], LLM],
    embedder_factory: Callable[[], Embedder],
) -> None:
    """Run every queued AI module, committing after each so progress is visible."""
    async with session_factory() as session:
        evaluation = await get_evaluation(session, evaluation_id)
        if evaluation is None:
            raise ValueError(f"Evaluation {evaluation_id} not found")
        company = await session.get(Company, evaluation.company_id)
        if company is None:
            raise ValueError(f"Company {evaluation.company_id} not found")
        # Plain values: ORM objects expire after a rollback and can't lazy-load in async code.
        cid, cname = company.id, company.name
        try:
            llm, embedder = llm_factory(), embedder_factory()
        except AIConfigurationError as exc:
            for module in AI_ONLY_MODULES:
                await _set(session, evaluation_id, module, status=FindingStatus.NOT_RUN, error=str(exc))
            await session.commit()
            return

        async def step(module: str, work: Callable[[], Any]) -> Any:
            await _set(session, evaluation_id, module, status=FindingStatus.RUNNING)
            await session.commit()
            try:
                return await work()
            except NoPassagesError as exc:
                await _set(session, evaluation_id, module, status=FindingStatus.NOT_RUN, error=str(exc))
            except Exception as exc:  # recorded on the finding; the next module still runs
                log.exception("module_failed", module=module, evaluation_id=str(evaluation_id))
                await session.rollback()
                await _set(
                    session,
                    evaluation_id,
                    module,
                    status=FindingStatus.FAILED,
                    error=f"{type(exc).__name__}: {exc}"[:2000],
                )
            finally:
                await session.commit()
            return None

        # Debt Structure: add borrowing-level detail to the rule-based metrics.
        debt_finding = await session.scalar(
            select(ModuleFinding).where(
                ModuleFinding.evaluation_id == evaluation_id, ModuleFinding.module == "debt_structure"
            )
        )
        base_debt = dict(debt_finding.data) if debt_finding else {}
        base_summary = debt_finding.summary if debt_finding else ""
        base_sources = {e["source_document_id"] for e in (debt_finding.evidence if debt_finding else [])}
        out = await step("debt_structure", lambda: run_debt_extraction(session, llm, embedder, cid, cname))
        if out is not None:
            await _set(
                session,
                evaluation_id,
                "debt_structure",
                status=FindingStatus.COMPLETE,
                summary=base_summary,
                data={**base_debt, **out.data},
                evidence=await _evidence(session, out.source_document_ids | base_sources),
            )
        else:
            # Keep the rule-based metrics; record why the extraction did not complete.
            failed = await session.scalar(
                select(ModuleFinding).where(
                    ModuleFinding.evaluation_id == evaluation_id, ModuleFinding.module == "debt_structure"
                )
            )
            reason = failed.error if failed else None
            await _set(
                session,
                evaluation_id,
                "debt_structure",
                status=FindingStatus.PARTIAL,
                summary=base_summary,
                data=base_debt,
                evidence=await _evidence(session, base_sources),
                error=f"Borrowing-level extraction did not complete: {reason}",
            )
        await session.commit()

        out = await step(
            "related_party_transactions", lambda: run_rpt_extraction(session, llm, embedder, cid, cname)
        )
        if out is not None:
            total = out.data["total_transactions_current_cr"]
            summary = (
                f"{len(out.data['lines'])} related-party lines extracted ({out.data['unverified_lines']} with amounts "
                f"that could not be verified). Transactions in the latest year total "
                f"{'n/a' if total is None else f'₹{total:,.1f} Cr'}."
            )
            await _set(
                session,
                evaluation_id,
                "related_party_transactions",
                status=FindingStatus.COMPLETE,
                summary=summary,
                data=out.data,
                evidence=await _evidence(session, out.source_document_ids),
            )
            if total is not None:
                await _store_rpt_fact(session, cid, total, out.source_document_ids)
                await _warnings_finding(session, evaluation_id, cid)  # the RPT check can now run
            await session.commit()

        def research(m: str) -> Callable[[], Any]:
            return lambda: run_research_module(session, llm, embedder, cid, cname, m)

        for module in RESEARCH_SPECS:
            out = await step(module, research(module))
            if out is not None:
                await _set(
                    session,
                    evaluation_id,
                    module,
                    status=FindingStatus.COMPLETE,
                    summary=out.summary,
                    data=out.data,
                    evidence=await _evidence(session, out.source_document_ids),
                )
                await session.commit()

        findings = {
            f.module: {"summary": f.summary, "data": f.data}
            for f in await session.scalars(
                select(ModuleFinding).where(ModuleFinding.evaluation_id == evaluation_id)
            )
        }
        await _set(session, evaluation_id, "why_not_invest", status=FindingStatus.RUNNING)
        await session.commit()
        try:
            narrative = await run_why_not_invest(llm, cname, findings)
            await _why_not_invest_draft(session, evaluation_id, narrative.model_dump())
        except Exception as exc:
            log.exception("why_not_invest_failed", evaluation_id=str(evaluation_id))
            await session.rollback()
            await _why_not_invest_draft(session, evaluation_id, None)
            await _set(
                session,
                evaluation_id,
                "why_not_invest",
                status=FindingStatus.PARTIAL,
                summary="Rule-based concerns only.",
                error=f"AI narrative failed: {exc}"[:2000],
            )
        session.add(
            AuditEvent(
                entity_type="evaluation",
                entity_id=evaluation_id,
                action="research_completed",
                actor="system",
                details={},
            )
        )
        await session.commit()


async def get_evaluation(session: AsyncSession, evaluation_id: uuid.UUID) -> Evaluation | None:
    return await session.scalar(
        select(Evaluation)
        .where(Evaluation.id == evaluation_id)
        .options(selectinload(Evaluation.findings))
        .execution_options(populate_existing=True)
    )
