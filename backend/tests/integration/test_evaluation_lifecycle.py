"""End-to-end evaluation lifecycle against a real Postgres test database, with fake AI clients.

Needs TEST_DATABASE_URL (defaults to the local evaluation_test database); skipped when unreachable.
"""

import hashlib
import os
import re
import uuid
from collections.abc import AsyncIterator
from datetime import date
from decimal import Decimal
from typing import Any, TypeVar

import pytest
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.storage import LocalStore
from app.models import AuditEvent, Base, Company, CompanyPeer, FinancialFact
from app.models.company import Coverage, ReportingBasis
from app.modules.ingestion.pipeline import DocumentInput, embed_document, extract_document, register_document
from app.modules.reporting.export import to_markdown
from app.modules.research.schemas import (
    BorrowingLine,
    Claim,
    DebtExtraction,
    EvidenceRef,
    ModuleResearch,
    RptExtraction,
    RptLine,
    WhyNotInvest,
    WhyNotInvestReason,
)
from app.modules.workflow import actions
from app.modules.workflow.evaluation_service import create_evaluation, get_evaluation, run_research

TEST_DB = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://evaluation:evaluation@localhost:5433/evaluation_test"
)
T = TypeVar("T", bound=BaseModel)
FY25, FY26 = date(2025, 3, 31), date(2026, 3, 31)

DOC_TEXT = [
    "Management expects revenue to grow 25 percent next year as the new plant in Pune ramps up.",
    "Term loan from State Bank of India 500.00 secured by hypothecation of plant and machinery.",
    "Sale of goods to Acme Promoter Holdings Private Limited 120.50 during the year.",
    "Key risk: dependence on a single supplier for lithium cells imported from China.",
]


class FakeEmbedder:
    async def embed(self, texts: list[str], *, input_type: str) -> list[list[float]]:
        out = []
        for t in texts:
            seed = hashlib.sha256(t.encode()).digest()
            out.append([(seed[i % 32] - 128) / 128 for i in range(1024)])
        return out


class FakeLLM:
    """Returns schema-shaped answers that quote the passages it was given (plus one invented quote)."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def structured(self, *, system: str, prompt: str, schema: type[T]) -> T:
        self.calls.append(schema.__name__)
        passages = dict(re.findall(r'<passage id="(P\d+)"[^>]*>\n(.*?)\n</passage>', prompt, re.S))

        def find(word: str) -> tuple[str, str]:
            pid, body = next((p, b) for p, b in passages.items() if word in b)
            return pid, body

        result: Any
        if schema is ModuleResearch:
            pid, body = next(iter(passages.items()))
            result = ModuleResearch(
                summary="Grounded summary.",
                claims=[
                    Claim(
                        statement="Real claim",
                        topic="t",
                        sentiment="negative",
                        evidence=[EvidenceRef(passage_id=pid, quote=body[:60])],
                    ),
                    Claim(
                        statement="Invented claim",
                        topic="t",
                        sentiment="positive",
                        evidence=[EvidenceRef(passage_id=pid, quote="this sentence is not in any passage")],
                    ),
                ],
                open_questions=["What is the order book?"],
            )
        elif schema is DebtExtraction:
            pid, body = find("Term loan")
            result = DebtExtraction(
                period_label="31 March 2026",
                observations=[],
                borrowings=[
                    BorrowingLine(
                        lender_or_instrument="State Bank of India",
                        facility_type="term loan",
                        secured=True,
                        maturity="non_current",
                        amount_as_reported="500.00",
                        unit_as_reported="crore",
                        interest_rate=None,
                        repayment_terms=None,
                        evidence=EvidenceRef(passage_id=pid, quote=body),
                    )
                ],
            )
        elif schema is RptExtraction:
            pid, body = find("Sale of goods")
            result = RptExtraction(
                period_label="FY2026",
                observations=[],
                lines=[
                    RptLine(
                        related_party="Acme Promoter Holdings",
                        relationship="promoter entity",
                        nature="sale of goods",
                        kind="transaction",
                        year="current",
                        amount_as_reported="120.50",
                        unit_as_reported="crore",
                        evidence=EvidenceRef(passage_id=pid, quote=body),
                    )
                ],
            )
        elif schema is WhyNotInvest:
            result = WhyNotInvest(
                summary="AI case against.",
                mitigating_factors=["Low debt"],
                reasons=[
                    WhyNotInvestReason(
                        title="Supplier risk",
                        explanation="Single supplier.",
                        severity="high",
                        based_on=["company_risks"],
                    )
                ],
            )
        else:
            raise AssertionError(schema)
        return result  # type: ignore[no-any-return]


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(TEST_DB)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:  # pragma: no cover - environment dependent
        await engine.dispose()
        pytest.skip(f"Test database unavailable: {exc}")
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


def _facts(company_id: uuid.UUID, values: dict[str, dict[date, float]]) -> list[FinancialFact]:
    return [
        FinancialFact(
            company_id=company_id,
            metric=m,
            period_end=p,
            period_type="FY",
            basis=ReportingBasis.CONSOLIDATED,
            value=Decimal(str(v)),
            unit="INR_CR",
        )
        for m, series in values.items()
        for p, v in series.items()
    ]


BASE = {
    "revenue": {FY25: 1000, FY26: 1300},
    "cost_of_revenue": {FY26: 800},
    "gross_profit": {FY25: 300, FY26: 500},
    "ebitda": {FY26: 200},
    "ebit": {FY26: 150},
    "net_profit": {FY25: 60, FY26: 90},
    "profit_before_tax": {FY26: 120},
    "tax_expense": {FY26: 30},
    "interest_expense": {FY26: 20},
    "operating_cash_flow": {FY25: 50, FY26: 80},
    "total_debt": {FY25: 200, FY26: 250},
    "equity": {FY26: 900},
    "total_assets": {FY26: 1500},
    "total_current_liabilities": {FY26: 400},
    "receivables": {FY26: 100},
    "inventory": {FY26: 120},
    "accounts_payable": {FY26: 90},
    "shares_outstanding": {FY25: 100, FY26: 100},
}


def _pdf(lines: list[str]) -> bytes:
    """A minimal valid PDF with one page per line (no extra dependencies)."""
    objects = ["<< /Type /Catalog /Pages 2 0 R >>"]
    kids = " ".join(f"{3 + i * 2} 0 R" for i in range(len(lines)))
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(lines)} >>")
    font_id = 3 + len(lines) * 2
    for i, line in enumerate(lines):
        content = f"BT /F1 9 Tf 20 700 Td ({line}) Tj ET".encode()
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {4 + i * 2} 0 R "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> >>"
        )
        objects.append(f"<< /Length {len(content)} >>\nstream\n{content.decode()}\nendstream")
    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    out, offsets = b"%PDF-1.4\n", []
    for n, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{n} 0 obj\n{obj}\nendobj\n".encode()
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += "".join(f"{o:010d} 00000 n \n" for o in offsets).encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    return out


async def test_full_lifecycle(session_factory: async_sessionmaker[AsyncSession], tmp_path: Any) -> None:
    store = LocalStore(tmp_path)
    async with session_factory() as session:
        company = Company(name="Test Motors Ltd", nse_symbol="TESTMOT")
        peer = Company(name="Peer Motors Ltd", nse_symbol="PEERMOT", coverage=Coverage.PEER)
        session.add_all([company, peer])
        await session.flush()
        session.add_all(_facts(company.id, BASE))
        session.add_all(_facts(peer.id, {**BASE, "net_profit": {FY25: 100, FY26: 200}}))
        session.add(CompanyPeer(company_id=company.id, peer_company_id=peer.id))

        # Ingestion: register (idempotent), extract, embed.
        doc = DocumentInput(
            company=company,
            doc_type="annual_report",
            title="Test Motors AR FY2026",
            period_end=FY26,
            filing_date=None,
            url="https://www.bseindia.com/x.pdf",
            data=_pdf(DOC_TEXT),
        )
        source = await register_document(session, store, doc)
        assert (await register_document(session, store, doc)).id == source.id
        assert await extract_document(session, store, source) == len(DOC_TEXT)
        assert await embed_document(session, FakeEmbedder(), source) == len(DOC_TEXT)
        assert source.ingestion_status == "embedded" and source.is_primary
        await session.commit()

        evaluation = await create_evaluation(session, company, actor="analyst@test")
        findings = {f.module: f for f in evaluation.findings}
        assert len(findings) == 10
        assert findings["financial_warnings"].status == "complete"
        assert findings["competitors"].status == "complete"
        assert findings["debt_structure"].status == "partial"
        # No API keys in tests: AI modules are recorded as not run, with the reason.
        assert findings["company_risks"].status == "not_run" and "ANTHROPIC_API_KEY" in (
            findings["company_risks"].error or ""
        )
        rpt_before = next(
            r
            for r in findings["financial_warnings"].data["results"]
            if r["check"] == "related_party_transactions"
        )
        assert rpt_before["status"] == "not_assessed"
        evaluation_id, company_id = evaluation.id, company.id

    llm = FakeLLM()
    await run_research(session_factory, evaluation_id, llm_factory=lambda: llm, embedder_factory=FakeEmbedder)

    async with session_factory() as session:
        evaluation = await get_evaluation(session, evaluation_id)
        assert evaluation is not None
        findings = {f.module: f for f in evaluation.findings}
        assert {f.status for f in findings.values()} == {"complete"}, {
            m: (f.status, f.error) for m, f in findings.items()
        }

        claims = findings["company_risks"].data["claims"]
        assert [c["supported"] for c in claims] == [True, False]  # invented quote caught
        assert findings["company_risks"].data["unsupported_claims"] == 1

        debt = findings["debt_structure"].data
        assert debt["borrowings"][0]["amount_cr"] == 500.0 and debt["secured_share"] == 1.0
        assert debt["years"], "rule-based metrics kept alongside the extraction"

        rpt = findings["related_party_transactions"].data
        assert rpt["total_transactions_current_cr"] == pytest.approx(120.5)
        stored = await session.scalar(
            select(FinancialFact).where(
                FinancialFact.company_id == company_id, FinancialFact.metric == "rpt_value"
            )
        )
        assert stored is not None and float(stored.value) == pytest.approx(120.5)
        rpt_after = next(
            r
            for r in findings["financial_warnings"].data["results"]
            if r["check"] == "related_party_transactions"
        )
        assert rpt_after["status"] != "not_assessed"  # warning re-run with extracted RPT

        assert findings["why_not_invest"].data["ai"]["reasons"][0]["title"] == "Supplier risk"
        assert findings["why_not_invest"].data["rule_based_flags"] is not None

        # Analyst workflow
        risks = findings["company_risks"]
        await actions.add_comment(session, risks, "analyst@test", "Check the supplier contract.")
        with pytest.raises(actions.WorkflowError, match="reason"):
            await actions.set_override(session, evaluation, risks, "analyst@test", "Lower risk", None)
        await actions.set_override(
            session, evaluation, risks, "analyst@test", "Lower risk", "Second supplier signed"
        )
        with pytest.raises(actions.WorkflowError):
            await actions.approve(session, evaluation, "lead@test")  # must be in review first
        await actions.submit_for_review(session, evaluation, "analyst@test")
        await actions.approve(session, evaluation, "lead@test")
        with pytest.raises(actions.WorkflowError, match="locked"):
            await actions.set_override(session, evaluation, risks, "analyst@test", "Again", "x")

        trail = [e.action for e in await actions.audit_trail(session, evaluation)]
        assert trail[0] == "created" and "research_completed" in trail and trail[-1] == "approved"
        assert {"commented", "overridden", "submitted_for_review"} <= set(trail)
        assert await session.scalar(select(AuditEvent).where(AuditEvent.action == "approved"))

        company = await session.get(Company, company_id)
        assert company is not None
        report = to_markdown(evaluation, company)
        assert (
            "# Evaluation: Test Motors Ltd" in report
            and "Analyst override" in report
            and "(unsupported)" in report
        )

    assert llm.calls.count("ModuleResearch") == 4 and "WhyNotInvest" in llm.calls
