from datetime import date

from pydantic import BaseModel, Field

from app.modules.financial_engine.warnings import WarningCheck, WarningStatus


class WarningInputs(BaseModel):
    """Inputs for the eight checks, normally assembled from normalised `financial_facts`."""

    total_debt: float
    equity: float
    receivable_days: float
    inventory_days: float
    payable_days: float
    cumulative_ocf: float
    cumulative_net_profit: float
    pledged_pct_of_promoter: float = Field(ge=0, le=1)
    promoter_holding_change_pp: float
    rpt_value: float
    revenue: float
    shares_start: float = Field(gt=0)
    shares_end: float = Field(gt=0)
    effective_tax_rate: float
    payout_ratio: float
    roce: float | None


class WarningResultRead(BaseModel):
    check: WarningCheck
    status: WarningStatus
    value: float | None
    explanation: str
    inputs: dict[str, float | None]
    source_document_ids: list[str] = []


class WarningReport(BaseModel):
    formula_version: str
    as_of: date | None = None
    results: list[WarningResultRead]
