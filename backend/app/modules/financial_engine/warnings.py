"""The eight financial warning checks.

Thresholds below are PLACEHOLDERS until the formula catalogue is signed off in Phase 1
("Approved warning formulas and thresholds" is an open decision). Every evaluation stores
`formula_version` so results stay reproducible when thresholds change.

These rules apply to non-financial companies only. Banks, NBFCs and insurers need their own
rule templates.
"""

import enum
from dataclasses import dataclass, field

from app.modules.financial_engine.metrics import cash_conversion, safe_ratio


class WarningStatus(enum.StrEnum):
    CLEAR = "clear"
    WATCH = "watch"
    FLAG = "flag"
    NOT_ASSESSED = "not_assessed"  # required data missing, or the check is not meaningful


class WarningCheck(enum.StrEnum):
    DEBT = "debt"
    WORKING_CAPITAL = "working_capital"
    OPERATING_CASH_FLOW = "operating_cash_flow"
    PROMOTER_HOLDING = "promoter_holding_pledging"
    RPT = "related_party_transactions"
    DILUTION = "dilution"
    TAX_DIVIDEND = "tax_dividend"
    ROCE = "roce"


@dataclass(frozen=True)
class WarningResult:
    check: WarningCheck
    status: WarningStatus
    value: float | None
    explanation: str
    inputs: dict[str, float | None] = field(default_factory=dict)
    source_document_ids: tuple[str, ...] = ()


def not_assessed(
    check: WarningCheck, reason: str, inputs: dict[str, float | None] | None = None
) -> WarningResult:
    return WarningResult(check, WarningStatus.NOT_ASSESSED, None, reason, inputs or {})


def _grade(value: float | None, watch: float, flag: float, *, higher_is_worse: bool = True) -> WarningStatus:
    if value is None:
        return WarningStatus.WATCH
    if higher_is_worse:
        if value >= flag:
            return WarningStatus.FLAG
        return WarningStatus.WATCH if value >= watch else WarningStatus.CLEAR
    if value <= flag:
        return WarningStatus.FLAG
    return WarningStatus.WATCH if value <= watch else WarningStatus.CLEAR


def debt_check(total_debt: float, equity: float) -> WarningResult:
    de = safe_ratio(total_debt, equity)
    return WarningResult(
        WarningCheck.DEBT,
        _grade(de, watch=1.0, flag=2.0),
        de,
        "Debt-to-equity ratio.",
        {"total_debt": total_debt, "equity": equity},
    )


def working_capital_check(
    receivable_days: float, inventory_days: float, payable_days: float
) -> WarningResult:
    ccc = receivable_days + inventory_days - payable_days
    return WarningResult(
        WarningCheck.WORKING_CAPITAL,
        _grade(ccc, watch=90, flag=150),
        ccc,
        "Cash conversion cycle in days.",
        {"receivable_days": receivable_days, "inventory_days": inventory_days, "payable_days": payable_days},
    )


def operating_cash_flow_check(cumulative_ocf: float, cumulative_net_profit: float) -> WarningResult:
    inputs: dict[str, float | None] = {
        "cumulative_ocf": cumulative_ocf,
        "cumulative_net_profit": cumulative_net_profit,
    }
    if cumulative_net_profit <= 0:
        # OCF / profit is meaningless for a loss-making company: judge the cash flow itself.
        return WarningResult(
            WarningCheck.OPERATING_CASH_FLOW,
            WarningStatus.FLAG if cumulative_ocf < 0 else WarningStatus.WATCH,
            None,
            "Loss-making over the review window, so cash conversion is not meaningful; "
            + (
                "cumulative operating cash flow is negative."
                if cumulative_ocf < 0
                else "cumulative operating cash flow is positive despite losses."
            ),
            inputs,
        )
    ratio = cash_conversion(cumulative_ocf, cumulative_net_profit)
    return WarningResult(
        WarningCheck.OPERATING_CASH_FLOW,
        _grade(ratio, watch=0.8, flag=0.5, higher_is_worse=False),
        ratio,
        "Cumulative operating cash flow / cumulative net profit over the review window.",
        inputs,
    )


def promoter_check(pledged_pct_of_promoter: float, promoter_holding_change_pp: float) -> WarningResult:
    status = _grade(pledged_pct_of_promoter, watch=0.10, flag=0.25)
    if promoter_holding_change_pp <= -5 and status is WarningStatus.CLEAR:
        status = WarningStatus.WATCH
    return WarningResult(
        WarningCheck.PROMOTER_HOLDING,
        status,
        pledged_pct_of_promoter,
        "Share of promoter holding pledged, adjusted for large promoter sell-downs.",
        {
            "pledged_pct_of_promoter": pledged_pct_of_promoter,
            "promoter_holding_change_pp": promoter_holding_change_pp,
        },
    )


def rpt_check(rpt_value: float, revenue: float) -> WarningResult:
    ratio = safe_ratio(rpt_value, revenue)
    return WarningResult(
        WarningCheck.RPT,
        _grade(ratio, watch=0.05, flag=0.10),
        ratio,
        "Related-party transactions as a share of revenue.",
        {"rpt_value": rpt_value, "revenue": revenue},
    )


def dilution_check(shares_start: float, shares_end: float) -> WarningResult:
    growth = safe_ratio(shares_end - shares_start, shares_start)
    return WarningResult(
        WarningCheck.DILUTION,
        _grade(growth, watch=0.05, flag=0.15),
        growth,
        "Growth in share count over the review window.",
        {"shares_start": shares_start, "shares_end": shares_end},
    )


def tax_dividend_check(effective_tax_rate: float, payout_ratio: float) -> WarningResult:
    status = WarningStatus.CLEAR
    if effective_tax_rate < 0.15 or payout_ratio > 1.0:
        status = WarningStatus.WATCH
    if effective_tax_rate < 0.05:
        status = WarningStatus.FLAG
    return WarningResult(
        WarningCheck.TAX_DIVIDEND,
        status,
        effective_tax_rate,
        "Unusually low effective tax rate or dividends above earnings.",
        {"effective_tax_rate": effective_tax_rate, "payout_ratio": payout_ratio},
    )


def roce_check(roce_value: float | None) -> WarningResult:
    return WarningResult(
        WarningCheck.ROCE,
        _grade(roce_value, watch=0.12, flag=0.08, higher_is_worse=False),
        roce_value,
        "Return on capital employed.",
        {"roce": roce_value},
    )
