"""Run one AI module: retrieve passages → structured LLM output → verify every quote in code.

Outputs are plain dicts ready to store on a ModuleFinding. Unverified quotes are kept but marked,
and a claim without a verified quote is marked unsupported (never presented as fact).
"""

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.modules.financial_engine.debt import amount_in_quote, parse_amount
from app.modules.research.clients import LLM, Embedder
from app.modules.research.prompts import (
    DEBT_SPEC,
    RESEARCH_SPECS,
    RPT_SPEC,
    SYSTEM_PROMPT,
    WHY_NOT_INVEST_TASK,
    ResearchSpec,
)
from app.modules.research.retrieval import Passage, evidence_entry, format_passages, retrieve, verify_quote
from app.modules.research.schemas import (
    Claim,
    DebtExtraction,
    EvidenceRef,
    ModuleResearch,
    RptExtraction,
    WhyNotInvest,
)


@dataclass(frozen=True)
class ModuleOutput:
    summary: str
    data: dict[str, Any]
    source_document_ids: set[str]


class NoPassagesError(RuntimeError):
    pass


async def _passages(
    session: AsyncSession, embedder: Embedder, company_id: uuid.UUID, spec: ResearchSpec
) -> dict[str, Passage]:
    settings = get_settings()
    passages = await retrieve(
        session,
        embedder,
        company_id,
        spec.queries,
        per_query=settings.retrieval_passages_per_query,
        max_passages=spec.max_passages or settings.retrieval_max_passages,
        doc_types=spec.doc_types,
    )
    if not passages:
        kinds = ", ".join(spec.doc_types) if spec.doc_types else "documents"
        raise NoPassagesError(f"No embedded {kinds} found for this company")
    return {p.passage_id: p for p in passages}


def _prompt(company_name: str, spec: ResearchSpec, passages: dict[str, Passage]) -> str:
    return (
        f"Company: {company_name}\nModule: {spec.title}\n\n<passages>\n{format_passages(list(passages.values()))}\n"
        f"</passages>\n\nTask: {spec.task}"
    )


def _verify_ref(passages: dict[str, Passage], ref: EvidenceRef) -> dict[str, Any]:
    return evidence_entry(verify_quote(passages, ref.passage_id, ref.quote), ref.passage_id, ref.quote)


def _verify_claims(passages: dict[str, Passage], claims: list[Claim]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for claim in claims:
        evidence = [_verify_ref(passages, ref) for ref in claim.evidence]
        out.append(
            {
                "statement": claim.statement,
                "topic": claim.topic,
                "sentiment": claim.sentiment,
                "supported": any(e["verified"] for e in evidence),
                "evidence": evidence,
            }
        )
    return out


def _sources(*groups: list[dict[str, Any]]) -> set[str]:
    return {
        e["source_document_id"] for g in groups for e in g if e.get("verified") and e["source_document_id"]
    }


async def run_research_module(
    session: AsyncSession, llm: LLM, embedder: Embedder, company_id: uuid.UUID, company_name: str, module: str
) -> ModuleOutput:
    spec = RESEARCH_SPECS[module]
    passages = await _passages(session, embedder, company_id, spec)
    result = await llm.structured(
        system=SYSTEM_PROMPT, prompt=_prompt(company_name, spec, passages), schema=ModuleResearch
    )
    claims = _verify_claims(passages, result.claims)
    unsupported = sum(1 for c in claims if not c["supported"])
    return ModuleOutput(
        summary=result.summary,
        data={
            "claims": claims,
            "open_questions": result.open_questions,
            "passages_considered": len(passages),
            "unsupported_claims": unsupported,
        },
        source_document_ids=_sources(*(c["evidence"] for c in claims)),
    )


async def run_debt_extraction(
    session: AsyncSession, llm: LLM, embedder: Embedder, company_id: uuid.UUID, company_name: str
) -> ModuleOutput:
    passages = await _passages(session, embedder, company_id, DEBT_SPEC)
    result = await llm.structured(
        system=SYSTEM_PROMPT, prompt=_prompt(company_name, DEBT_SPEC, passages), schema=DebtExtraction
    )
    lines: list[dict[str, Any]] = []
    for b in result.borrowings:
        evidence = _verify_ref(passages, b.evidence)
        amount_ok = evidence["verified"] and amount_in_quote(b.amount_as_reported, b.evidence.quote)
        lines.append(
            {
                "lender_or_instrument": b.lender_or_instrument,
                "facility_type": b.facility_type,
                "secured": b.secured,
                "maturity": b.maturity,
                "amount_as_reported": b.amount_as_reported,
                "unit_as_reported": b.unit_as_reported,
                "amount_cr": parse_amount(b.amount_as_reported, b.unit_as_reported) if amount_ok else None,
                "amount_verified": amount_ok,
                "interest_rate": b.interest_rate,
                "repayment_terms": b.repayment_terms,
                "evidence": evidence,
            }
        )
    observations = _verify_claims(passages, result.observations)
    verified_amounts = [line["amount_cr"] for line in lines if line["amount_cr"] is not None]
    secured = sum(
        line["amount_cr"] for line in lines if line["amount_cr"] is not None and line["secured"] is True
    )
    total = sum(verified_amounts)
    return ModuleOutput(
        summary="",
        data={
            "period_label": result.period_label,
            "borrowings": lines,
            "extracted_total_cr": total if verified_amounts else None,
            "secured_share": secured / total if total else None,
            "observations": observations,
        },
        source_document_ids=_sources(
            [line["evidence"] for line in lines], *(o["evidence"] for o in observations)
        ),
    )


async def run_rpt_extraction(
    session: AsyncSession, llm: LLM, embedder: Embedder, company_id: uuid.UUID, company_name: str
) -> ModuleOutput:
    passages = await _passages(session, embedder, company_id, RPT_SPEC)
    result = await llm.structured(
        system=SYSTEM_PROMPT, prompt=_prompt(company_name, RPT_SPEC, passages), schema=RptExtraction
    )
    lines: list[dict[str, Any]] = []
    for line in result.lines:
        evidence = _verify_ref(passages, line.evidence)
        amount_ok = evidence["verified"] and amount_in_quote(line.amount_as_reported, line.evidence.quote)
        lines.append(
            {
                "related_party": line.related_party,
                "relationship": line.relationship,
                "nature": line.nature,
                "kind": line.kind,
                "year": line.year,
                "amount_as_reported": line.amount_as_reported,
                "unit_as_reported": line.unit_as_reported,
                "amount_cr": parse_amount(line.amount_as_reported, line.unit_as_reported)
                if amount_ok
                else None,
                "amount_verified": amount_ok,
                "evidence": evidence,
            }
        )
    observations = _verify_claims(passages, result.observations)

    def total(kind: str, year: str) -> float | None:
        amounts = [
            abs(x["amount_cr"])
            for x in lines
            if x["kind"] == kind and x["year"] == year and x["amount_cr"] is not None
        ]
        return sum(amounts) if amounts else None

    by_party: dict[str, float] = {}
    for x in lines:
        if x["kind"] == "transaction" and x["year"] == "current" and x["amount_cr"] is not None:
            by_party[x["related_party"]] = by_party.get(x["related_party"], 0.0) + abs(x["amount_cr"])
    return ModuleOutput(
        summary="",
        data={
            "period_label": result.period_label,
            "lines": lines,
            "total_transactions_current_cr": total("transaction", "current"),
            "total_transactions_previous_cr": total("transaction", "previous"),
            "total_balances_current_cr": total("outstanding_balance", "current"),
            "top_parties": [
                {"related_party": k, "amount_cr": v}
                for k, v in sorted(by_party.items(), key=lambda kv: kv[1], reverse=True)[:10]
            ],
            "unverified_lines": sum(1 for x in lines if not x["amount_verified"]),
            "observations": observations,
        },
        source_document_ids=_sources([x["evidence"] for x in lines], *(o["evidence"] for o in observations)),
    )


async def run_why_not_invest(
    llm: LLM, company_name: str, findings: dict[str, dict[str, Any]]
) -> WhyNotInvest:
    blocks = []
    for module, finding in findings.items():
        if module == "why_not_invest":
            continue
        blocks.append(
            f'<finding module="{module}">\nSummary: {finding.get("summary", "")}\n{_compact(finding)}\n</finding>'
        )
    prompt = f"Company: {company_name}\n\n" + "\n\n".join(blocks) + f"\n\nTask: {WHY_NOT_INVEST_TASK}"
    return await llm.structured(system=SYSTEM_PROMPT, prompt=prompt, schema=WhyNotInvest)


def _compact(finding: dict[str, Any]) -> str:
    """A token-light view of a finding's data for the synthesis prompt."""
    data = finding.get("data", {})
    lines: list[str] = []
    for r in data.get("results", []):
        lines.append(f"- warning {r['check']}: {r['status']} ({r['explanation']})")
    for c in data.get("claims", []):
        if c.get("supported"):
            lines.append(f"- [{c['sentiment']}] {c['statement']}")
    for m in data.get("metrics", []):
        lines.append(f"- {m['label']}: company {m.get('subject')} vs peer median {m.get('peer_median')}")
    if years := data.get("years"):
        lines.append(f"- latest year: {years[-1]}")
    return "\n".join(lines[:40])
