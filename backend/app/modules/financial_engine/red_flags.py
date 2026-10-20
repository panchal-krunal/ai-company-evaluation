"""Rule-based first draft of 'Why Not Invest', assembled from the other modules' findings."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RedFlag:
    title: str
    explanation: str
    severity: str  # high | medium | low
    based_on: list[str]


CHECK_LABELS = {
    "debt": "High leverage",
    "working_capital": "Long working-capital cycle",
    "operating_cash_flow": "Weak cash conversion",
    "promoter_holding_pledging": "Promoter pledging / sell-down",
    "related_party_transactions": "Large related-party transactions",
    "dilution": "Shareholder dilution",
    "tax_dividend": "Unusual tax rate or payout",
    "roce": "Low return on capital",
}


def _describe(check: str, value: float | None, inputs: dict[str, Any], explanation: str) -> str:
    """The company's actual figure for a warning, in words."""
    if value is None:
        return explanation
    match check:
        case "debt":
            return f"Debt is {value:.2f}× equity."
        case "working_capital":
            return f"Cash conversion cycle of {value:.0f} days (receivables + inventory − payables)."
        case "operating_cash_flow":
            return f"Operating cash flow was only {value:.2f}× net profit over the review window."
        case "promoter_holding_pledging":
            return f"{value * 100:.1f}% of the promoters' holding is pledged."
        case "related_party_transactions":
            return f"Related-party transactions equal {value * 100:.1f}% of revenue."
        case "dilution":
            return f"Shares outstanding grew {value * 100:.1f}% in the latest year."
        case "tax_dividend":
            return f"Effective tax rate of {value * 100:.1f}%."
        case "roce":
            return f"Return on capital employed of {value * 100:.1f}%."
    return explanation


def draft_red_flags(findings: dict[str, dict[str, Any]]) -> list[RedFlag]:
    flags: list[RedFlag] = []

    for r in findings.get("financial_warnings", {}).get("results", []):
        if r["status"] in ("flag", "watch"):
            flags.append(
                RedFlag(
                    CHECK_LABELS.get(r["check"], r["check"]),
                    _describe(r["check"], r.get("value"), r.get("inputs", {}), r["explanation"]),
                    "high" if r["status"] == "flag" else "medium",
                    ["financial_warnings"],
                )
            )

    growth = findings.get("growth_analysis", {})
    years = growth.get("years", [])
    if years:
        latest = years[-1]
        if latest.get("net_margin") is not None and latest["net_margin"] < 0:
            flags.append(
                RedFlag(
                    "Loss-making",
                    "The company reported a net loss in the latest year.",
                    "high",
                    ["growth_analysis"],
                )
            )
        if latest.get("revenue_growth") is not None and latest["revenue_growth"] < 0:
            flags.append(
                RedFlag("Revenue decline", "Revenue fell in the latest year.", "medium", ["growth_analysis"])
            )

    debt_years = findings.get("debt_structure", {}).get("years", [])
    if debt_years:
        d = debt_years[-1]
        cover = d.get("interest_coverage")
        if cover is not None and cover < 1.5:
            explanation = (
                "Operating loss: EBIT does not cover interest at all in the latest year."
                if cover < 0
                else f"EBIT covers interest only {cover:.1f}× in the latest year."
            )
            flags.append(RedFlag("Thin interest cover", explanation, "high", ["debt_structure"]))
        if d.get("debt_to_ebitda") is not None and d["debt_to_ebitda"] > 4:
            flags.append(
                RedFlag(
                    "High debt relative to EBITDA",
                    f"Debt is {d['debt_to_ebitda']:.1f}× EBITDA.",
                    "medium",
                    ["debt_structure"],
                )
            )

    comparison = findings.get("competitors", {})
    worse = [
        m["label"]
        for m in comparison.get("metrics", [])
        if m.get("better_than_median") is False and m["key"] != "revenue"
    ]
    if len(worse) >= 3:
        flags.append(
            RedFlag(
                "Weaker than peers",
                f"Below the peer median on {', '.join(worse)}.",
                "medium",
                ["competitors"],
            )
        )

    for claim in findings.get("company_risks", {}).get("claims", []):
        if claim.get("sentiment") == "negative" and claim.get("supported"):
            flags.append(
                RedFlag(
                    claim.get("topic") or "Disclosed risk", claim["statement"], "medium", ["company_risks"]
                )
            )

    order = {"high": 0, "medium": 1, "low": 2}
    return sorted(flags, key=lambda f: order.get(f.severity, 3))
