"""Competitor comparison on the latest fiscal year, computed from stored figures."""

import statistics
from dataclasses import dataclass
from datetime import date

from app.modules.financial_engine.company_analysis import FactTable
from app.modules.financial_engine.metrics import margin, roce, safe_ratio

# Size metrics are ranked but not judged better or worse.
NEUTRAL = {"revenue"}

# (key, label, higher_is_better)
METRICS: list[tuple[str, str, bool]] = [
    ("revenue", "Revenue (₹ Cr)", True),
    ("revenue_growth", "Revenue growth", True),
    ("gross_margin", "Gross margin", True),
    ("ebitda_margin", "EBITDA margin", True),
    ("net_margin", "Net margin", True),
    ("roce", "RoCE", True),
    ("debt_to_equity", "Debt / equity", False),
    ("ocf_to_profit", "OCF / net profit", True),
]


@dataclass(frozen=True)
class CompanyRow:
    company_id: str
    name: str
    nse_symbol: str | None
    is_subject: bool
    period_end: date | None
    values: dict[str, float | None]
    source_document_ids: tuple[str, ...]


def latest_metrics(fy: FactTable) -> tuple[date | None, dict[str, float | None]]:
    years = fy.periods("revenue")
    if not years:
        return None, {key: None for key, _, _ in METRICS}
    y = years[-1]
    prev = years[-2] if len(years) > 1 else None
    revenue = fy.get("revenue", y)
    prev_revenue = fy.get("revenue", prev) if prev else None
    net_profit = fy.get("net_profit", y)
    ocf = fy.get("operating_cash_flow", y)
    assets, current_liabilities = fy.get("total_assets", y), fy.get("total_current_liabilities", y)
    ebit, debt, equity = fy.get("ebit", y), fy.get("total_debt", y), fy.get("equity", y)

    def m(metric: str) -> float | None:
        value = fy.get(metric, y)
        return None if value is None or not revenue else margin(value, revenue)

    return y, {
        "revenue": revenue,
        "revenue_growth": (
            safe_ratio(revenue - prev_revenue, prev_revenue)
            if revenue is not None and prev_revenue and prev_revenue > 0
            else None
        ),
        "gross_margin": m("gross_profit"),
        "ebitda_margin": m("ebitda"),
        "net_margin": m("net_profit"),
        "roce": _roce(ebit, assets, current_liabilities),
        "debt_to_equity": (
            safe_ratio(debt, equity) if debt is not None and equity is not None and equity > 0 else None
        ),
        "ocf_to_profit": (
            safe_ratio(ocf, net_profit)
            if ocf is not None and net_profit is not None and net_profit > 0
            else None
        ),
    }


def _roce(ebit: float | None, assets: float | None, current_liabilities: float | None) -> float | None:
    if ebit is None or assets is None or current_liabilities is None or assets - current_liabilities <= 0:
        return None
    return roce(ebit, assets - current_liabilities)


@dataclass(frozen=True)
class Comparison:
    rows: list[CompanyRow]
    peer_median: dict[str, float | None]
    subject_rank: dict[str, int | None]  # 1 = best among subject + peers
    better_than_median: dict[str, bool | None]


def compare(subject: CompanyRow, peers: list[CompanyRow]) -> Comparison:
    rows = [subject, *peers]
    median: dict[str, float | None] = {}
    rank: dict[str, int | None] = {}
    better: dict[str, bool | None] = {}
    for key, _, higher_is_better in METRICS:
        peer_values = [p.values[key] for p in peers if p.values.get(key) is not None]
        median[key] = statistics.median(peer_values) if peer_values else None  # type: ignore[type-var]
        value = subject.values.get(key)
        if value is None:
            rank[key], better[key] = None, None
            continue
        all_values = sorted(
            [v for v in (r.values.get(key) for r in rows) if v is not None], reverse=higher_is_better
        )
        rank[key] = all_values.index(value) + 1
        med = median[key]
        if med is None or key in NEUTRAL:
            better[key] = None
        else:
            better[key] = value > med if higher_is_better else value < med
    return Comparison(rows=rows, peer_median=median, subject_rank=rank, better_than_median=better)
