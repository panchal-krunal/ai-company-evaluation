"""Debt structure metrics from stored figures (borrowing-level detail comes from document extraction)."""

from dataclasses import dataclass
from datetime import date

from app.modules.financial_engine.company_analysis import FactTable
from app.modules.financial_engine.metrics import safe_ratio


@dataclass(frozen=True)
class DebtYear:
    period_end: date
    total_debt: float | None
    net_debt: float | None
    debt_to_equity: float | None
    debt_to_ebitda: float | None
    interest_coverage: float | None  # EBIT / interest expense
    implied_interest_rate: float | None  # interest expense / average debt
    short_term_share: float | None  # short-term + current maturities / total debt


def _cash(fy: FactTable, y: date) -> float | None:
    combined = fy.get("cash_and_short_term_investments", y)
    if combined is not None:
        return combined
    cash, investments = fy.get("cash_and_equivalents", y), fy.get("short_term_investments", y)
    return None if cash is None and investments is None else (cash or 0) + (investments or 0)


def debt_profile(fy: FactTable) -> list[DebtYear]:
    years = fy.periods("total_debt")
    out: list[DebtYear] = []
    for i, y in enumerate(years):
        debt = fy.get("total_debt", y)
        prev_debt = fy.get("total_debt", years[i - 1]) if i > 0 else None
        cash = _cash(fy, y)
        equity, ebitda = fy.get("equity", y), fy.get("ebitda", y)
        ebit, interest = fy.get("ebit", y), fy.get("interest_expense", y)
        short_parts = [fy.get("short_term_debt", y), fy.get("current_debt", y)]
        short = None if all(p is None for p in short_parts) else sum(p or 0 for p in short_parts)
        avg_debt = (debt + prev_debt) / 2 if debt is not None and prev_debt is not None else debt
        out.append(
            DebtYear(
                period_end=y,
                total_debt=debt,
                net_debt=None if debt is None or cash is None else debt - cash,
                debt_to_equity=safe_ratio(debt, equity)
                if debt is not None and equity and equity > 0
                else None,
                debt_to_ebitda=safe_ratio(debt, ebitda)
                if debt is not None and ebitda and ebitda > 0
                else None,
                interest_coverage=safe_ratio(ebit, interest) if ebit is not None and interest else None,
                implied_interest_rate=(
                    safe_ratio(interest, avg_debt) if interest is not None and avg_debt else None
                ),
                short_term_share=safe_ratio(short, debt) if short is not None and debt else None,
            )
        )
    return out


UNIT_TO_CRORE = {"crore": 1.0, "lakh": 0.01, "million": 0.1, "thousand": 0.0001, "rupees": 1e-7}


def parse_amount(text: str | None, unit: str) -> float | None:
    """'(1,234.56)' in lakh → -12.3456 crore. None when the text or unit can't be interpreted."""
    if not text or unit not in UNIT_TO_CRORE:
        return None
    cleaned = text.strip().replace(",", "").replace("₹", "").replace("Rs.", "").strip()
    negative = (cleaned.startswith("(") and cleaned.endswith(")")) or cleaned.startswith("-")
    cleaned = cleaned.strip("()- ")
    try:
        value = float(cleaned)
    except ValueError:
        return None
    return (-value if negative else value) * UNIT_TO_CRORE[unit]


def amount_in_quote(amount_text: str | None, quote: str) -> bool:
    """The printed amount must appear in the quoted text (digits compared without separators)."""
    if not amount_text:
        return False
    digits = "".join(ch for ch in amount_text if ch.isdigit() or ch == ".").strip(".")
    return bool(digits) and digits in "".join(ch for ch in quote if ch.isdigit() or ch == ".")
