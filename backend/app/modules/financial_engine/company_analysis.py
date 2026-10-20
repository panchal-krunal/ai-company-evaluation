"""Run the financial engine on a company's stored, normalised figures.

Every result records which source documents its inputs came from, so a figure on the dashboard
can be traced back to where it was published.
"""

import uuid
from dataclasses import dataclass, field, replace
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FinancialFact
from app.models.company import ReportingBasis
from app.modules.financial_engine import warnings as w
from app.modules.financial_engine.metrics import cagr, margin, roce, safe_ratio, yoy_growth

DAYS_IN_YEAR = 365


@dataclass
class FactTable:
    """In-memory view of one company's figures for a single basis and period type."""

    values: dict[tuple[str, date], float] = field(default_factory=dict)
    sources: dict[tuple[str, date], str] = field(default_factory=dict)

    def get(self, metric: str, period: date) -> float | None:
        return self.values.get((metric, period))

    def periods(self, metric: str) -> list[date]:
        return sorted(p for m, p in self.values if m == metric)

    def all_periods(self) -> list[date]:
        return sorted({p for _, p in self.values})

    def source_ids(self, metrics: list[str], periods: list[date]) -> tuple[str, ...]:
        ids = {self.sources[(m, p)] for m in metrics for p in periods if (m, p) in self.sources}
        return tuple(sorted(ids))


async def load_facts(
    session: AsyncSession, company_id: uuid.UUID, basis: ReportingBasis, period_type: str
) -> FactTable:
    rows = await session.scalars(
        select(FinancialFact).where(
            FinancialFact.company_id == company_id,
            FinancialFact.basis == basis,
            FinancialFact.period_type == period_type,
        )
    )
    table = FactTable()
    for fact in rows:
        key = (fact.metric, fact.period_end)
        table.values[key] = float(fact.value)
        if fact.source_document_id:
            table.sources[key] = str(fact.source_document_id)
    return table


def _with_sources(
    result: w.WarningResult, table: FactTable, metrics: list[str], periods: list[date]
) -> w.WarningResult:
    return replace(result, source_document_ids=table.source_ids(metrics, periods))


def _missing(table: FactTable, metrics: list[str], period: date) -> list[str]:
    return [m for m in metrics if table.get(m, period) is None]


def evaluate_warnings(
    fy: FactTable, quarterly: FactTable, *, review_years: int = 3
) -> tuple[date, list[w.WarningResult]]:
    """Run the eight checks as of the latest fiscal year. Returns (as_of, results)."""
    years = fy.periods("revenue")
    if not years:
        raise ValueError("No annual revenue figures stored for this company")
    latest = years[-1]
    window = years[-review_years:]
    prior = years[-2] if len(years) > 1 else None
    results: list[w.WarningResult] = []

    # 1. Debt
    if missing := _missing(fy, ["total_debt", "equity"], latest):
        results.append(w.not_assessed(w.WarningCheck.DEBT, f"Missing data: {', '.join(missing)}."))
    else:
        r = w.debt_check(fy.get("total_debt", latest) or 0, fy.get("equity", latest) or 0)
        results.append(_with_sources(r, fy, ["total_debt", "equity"], [latest]))

    # 2. Working capital (cash conversion cycle from year-end balances)
    wc_metrics = ["receivables", "inventory", "accounts_payable", "revenue", "cost_of_revenue"]
    if missing := _missing(fy, wc_metrics, latest):
        results.append(w.not_assessed(w.WarningCheck.WORKING_CAPITAL, f"Missing data: {', '.join(missing)}."))
    else:
        revenue = fy.get("revenue", latest) or 0
        cogs = fy.get("cost_of_revenue", latest) or 0
        receivable_days = (safe_ratio(fy.get("receivables", latest) or 0, revenue) or 0) * DAYS_IN_YEAR
        inventory_days = (safe_ratio(fy.get("inventory", latest) or 0, cogs) or 0) * DAYS_IN_YEAR
        payable_days = (safe_ratio(fy.get("accounts_payable", latest) or 0, cogs) or 0) * DAYS_IN_YEAR
        r = w.working_capital_check(receivable_days, inventory_days, payable_days)
        results.append(_with_sources(r, fy, wc_metrics, [latest]))

    # 3. Operating cash flow vs profit, cumulative over the review window
    if any(_missing(fy, ["operating_cash_flow", "net_profit"], y) for y in window):
        results.append(
            w.not_assessed(
                w.WarningCheck.OPERATING_CASH_FLOW, "Operating cash flow or net profit missing in window."
            )
        )
    else:
        ocf = sum(fy.get("operating_cash_flow", y) or 0 for y in window)
        profit = sum(fy.get("net_profit", y) or 0 for y in window)
        r = w.operating_cash_flow_check(ocf, profit)
        results.append(_with_sources(r, fy, ["operating_cash_flow", "net_profit"], window))

    # 4. Promoter holding & pledging (quarterly shareholding disclosures)
    holding_periods = quarterly.periods("promoter_holding_pct")
    pledge_periods = quarterly.periods("promoter_pledged_pct")
    holding_change = (
        (quarterly.get("promoter_holding_pct", holding_periods[-1]) or 0)
        - (quarterly.get("promoter_holding_pct", holding_periods[0]) or 0)
        if len(holding_periods) > 1
        else None
    )
    if not pledge_periods:
        results.append(
            _with_sources(
                w.not_assessed(
                    w.WarningCheck.PROMOTER_HOLDING,
                    "Promoter pledge data not loaded yet. Promoter holding changed by "
                    + (f"{holding_change:+.2f} pp" if holding_change is not None else "an unknown amount")
                    + " over the available quarters.",
                    {"promoter_holding_change_pp": holding_change},
                ),
                quarterly,
                ["promoter_holding_pct"],
                holding_periods,
            )
        )
    else:
        pledged = (quarterly.get("promoter_pledged_pct", pledge_periods[-1]) or 0) / 100
        r = w.promoter_check(pledged, holding_change or 0)
        results.append(
            _with_sources(r, quarterly, ["promoter_pledged_pct", "promoter_holding_pct"], holding_periods)
        )

    # 5. Related-party transactions
    if missing := _missing(fy, ["rpt_value", "revenue"], latest):
        results.append(
            w.not_assessed(
                w.WarningCheck.RPT, "Related-party transaction data not loaded yet (annual report RPT note)."
            )
        )
    else:
        r = w.rpt_check(fy.get("rpt_value", latest) or 0, fy.get("revenue", latest) or 0)
        results.append(_with_sources(r, fy, ["rpt_value", "revenue"], [latest]))

    # 6. Dilution, latest year (share counts before an IPO / bonus issue are not comparable)
    if (
        prior is None
        or _missing(fy, ["shares_outstanding"], latest)
        or _missing(fy, ["shares_outstanding"], prior)
    ):
        results.append(
            w.not_assessed(w.WarningCheck.DILUTION, "Need shares outstanding for two consecutive years.")
        )
    else:
        r = w.dilution_check(
            fy.get("shares_outstanding", prior) or 0, fy.get("shares_outstanding", latest) or 0
        )
        r = replace(r, explanation="Growth in shares outstanding over the latest fiscal year.")
        results.append(_with_sources(r, fy, ["shares_outstanding"], [prior, latest]))

    # 7. Tax & dividend
    pbt = fy.get("profit_before_tax", latest)
    if pbt is None:
        results.append(w.not_assessed(w.WarningCheck.TAX_DIVIDEND, "Missing data: profit_before_tax."))
    elif pbt <= 0:
        results.append(
            _with_sources(
                w.not_assessed(
                    w.WarningCheck.TAX_DIVIDEND,
                    "Not meaningful: the company made a pre-tax loss, so effective tax rate and "
                    "payout are undefined.",
                    {"profit_before_tax": pbt},
                ),
                fy,
                ["profit_before_tax"],
                [latest],
            )
        )
    elif _missing(fy, ["tax_expense", "net_profit"], latest):
        results.append(
            w.not_assessed(w.WarningCheck.TAX_DIVIDEND, "Missing data: tax_expense or net_profit.")
        )
    else:
        tax_rate = (fy.get("tax_expense", latest) or 0) / pbt
        payout = (
            safe_ratio(abs(fy.get("dividends_paid", latest) or 0), fy.get("net_profit", latest) or 0) or 0
        )
        r = w.tax_dividend_check(tax_rate, payout)
        results.append(_with_sources(r, fy, ["tax_expense", "profit_before_tax", "dividends_paid"], [latest]))

    # 8. RoCE = EBIT / (total assets - current liabilities)
    roce_metrics = ["ebit", "total_assets", "total_current_liabilities"]
    if missing := _missing(fy, roce_metrics, latest):
        results.append(w.not_assessed(w.WarningCheck.ROCE, f"Missing data: {', '.join(missing)}."))
    else:
        capital_employed = (fy.get("total_assets", latest) or 0) - (
            fy.get("total_current_liabilities", latest) or 0
        )
        r = w.roce_check(roce(fy.get("ebit", latest) or 0, capital_employed))
        r = replace(
            r, inputs={**r.inputs, "ebit": fy.get("ebit", latest), "capital_employed": capital_employed}
        )
        results.append(_with_sources(r, fy, roce_metrics, [latest]))

    return latest, results


@dataclass(frozen=True)
class YearMetrics:
    period_end: date
    revenue: float | None
    revenue_growth: float | None
    gross_margin: float | None
    ebitda_margin: float | None
    net_margin: float | None


@dataclass(frozen=True)
class GrowthAnalysis:
    years: list[YearMetrics]
    revenue_cagr_3y: float | None
    revenue_cagr_full: float | None
    full_period_years: int
    source_document_ids: tuple[str, ...]


def analyse_growth(fy: FactTable) -> GrowthAnalysis:
    years = fy.periods("revenue")
    revenues = [fy.get("revenue", y) or 0 for y in years]
    growth = [None, *yoy_growth(revenues)] if years else []

    def _margin(metric: str, y: date) -> float | None:
        value = fy.get(metric, y)
        return None if value is None else margin(value, fy.get("revenue", y) or 0)

    rows = [
        YearMetrics(
            period_end=y,
            revenue=fy.get("revenue", y),
            revenue_growth=g,
            gross_margin=_margin("gross_profit", y),
            ebitda_margin=_margin("ebitda", y),
            net_margin=_margin("net_profit", y),
        )
        for y, g in zip(years, growth, strict=True)
    ]
    n = len(years) - 1
    return GrowthAnalysis(
        years=rows,
        revenue_cagr_3y=cagr(revenues[-4], revenues[-1], 3) if len(revenues) >= 4 else None,
        revenue_cagr_full=cagr(revenues[0], revenues[-1], n) if n > 0 else None,
        full_period_years=max(n, 0),
        source_document_ids=fy.source_ids(["revenue", "gross_profit", "ebitda", "net_profit"], years),
    )
