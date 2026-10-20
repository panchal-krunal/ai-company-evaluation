"""Structured outputs the LLM must return. Every statement cites passages by ID with a verbatim quote."""

from typing import Literal

from pydantic import BaseModel, Field

Unit = Literal["crore", "lakh", "million", "thousand", "rupees", "unknown"]


class EvidenceRef(BaseModel):
    passage_id: str = Field(description='ID of the cited passage, e.g. "P3"')
    quote: str = Field(description="One sentence copied verbatim from that passage, without paraphrasing")


class Claim(BaseModel):
    statement: str = Field(description="One specific, factual statement in your own words")
    topic: str = Field(description="Short topic label, e.g. 'Capacity expansion'")
    sentiment: Literal["positive", "negative", "neutral"]
    evidence: list[EvidenceRef] = Field(
        description="Supporting quotes; leave empty if the passages do not support it"
    )


class ModuleResearch(BaseModel):
    summary: str = Field(description="3-5 sentence overview grounded only in the passages")
    claims: list[Claim]
    open_questions: list[str] = Field(description="Gaps or contradictions the analyst should investigate")


class BorrowingLine(BaseModel):
    lender_or_instrument: str = Field(description="Bank, NBFC, debenture series or instrument name")
    facility_type: str = Field(description="e.g. term loan, working capital, cash credit, NCD, lease")
    secured: bool | None = Field(
        description="True if stated as secured, False if unsecured, null if not stated"
    )
    maturity: Literal["current", "non_current", "unknown"]
    amount_as_reported: str | None = Field(description="Closing amount exactly as printed, e.g. '1,234.56'")
    unit_as_reported: Unit = Field(description="Unit the table states amounts in")
    interest_rate: str | None = Field(description="Rate as stated, e.g. 'MCLR + 1.25%' or '9.5% p.a.'")
    repayment_terms: str | None
    evidence: EvidenceRef


class DebtExtraction(BaseModel):
    period_label: str | None = Field(description="Balance sheet date the borrowings relate to")
    borrowings: list[BorrowingLine]
    observations: list[Claim] = Field(
        description="Credit ratings, covenants, defaults, refinancing, guarantees"
    )


class RptLine(BaseModel):
    related_party: str
    relationship: str = Field(description="e.g. subsidiary, promoter entity, key managerial personnel")
    nature: str = Field(description="e.g. sale of goods, purchase, loan given, remuneration, rent")
    kind: Literal["transaction", "outstanding_balance"]
    year: Literal["current", "previous"] = Field(description="Current reporting year or the comparative year")
    amount_as_reported: str = Field(description="Amount exactly as printed, e.g. '45.20'")
    unit_as_reported: Unit
    evidence: EvidenceRef


class RptExtraction(BaseModel):
    period_label: str | None
    lines: list[RptLine]
    observations: list[Claim] = Field(description="Unusual terms, loans to promoters, arm's-length concerns")


class WhyNotInvestReason(BaseModel):
    title: str
    explanation: str = Field(description="Why this is a reason not to invest, citing the module findings")
    severity: Literal["high", "medium", "low"]
    based_on: list[str] = Field(description="Module keys this reason is drawn from")


class WhyNotInvest(BaseModel):
    summary: str
    reasons: list[WhyNotInvestReason]
    mitigating_factors: list[str]
