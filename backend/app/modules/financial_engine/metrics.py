from collections.abc import Sequence
from itertools import pairwise


def safe_ratio(numerator: float, denominator: float) -> float | None:
    """Return numerator / denominator, or None when the denominator is zero."""
    if denominator == 0:
        return None
    return numerator / denominator


def cagr(start_value: float, end_value: float, years: float) -> float | None:
    """Compound annual growth rate. None when undefined (non-positive start/end or years)."""
    if years <= 0 or start_value <= 0 or end_value <= 0:
        return None
    growth: float = (end_value / start_value) ** (1 / years) - 1
    return growth


def margin(profit: float, revenue: float) -> float | None:
    return safe_ratio(profit, revenue)


def yoy_growth(series: Sequence[float]) -> list[float | None]:
    """Year-on-year growth for an ordered (oldest → newest) series."""
    return [None if prev <= 0 else (curr - prev) / prev for prev, curr in pairwise(series)]


def roce(ebit: float, capital_employed: float) -> float | None:
    """Return on capital employed = EBIT / (total assets - current liabilities)."""
    return safe_ratio(ebit, capital_employed)


def cash_conversion(operating_cash_flow: float, net_profit: float) -> float | None:
    """Operating cash flow / net profit — how much of reported profit turns into cash."""
    return safe_ratio(operating_cash_flow, net_profit)
