from datetime import date
from pathlib import Path

import pytest

from app.core.storage import LocalStore
from app.modules.financial_engine.company_analysis import FactTable
from app.modules.financial_engine.debt import amount_in_quote, debt_profile, parse_amount
from app.modules.financial_engine.peers import CompanyRow, compare
from app.modules.financial_engine.red_flags import draft_red_flags
from app.modules.research.retrieval import Passage, verify_quote

FY25, FY26 = date(2025, 3, 31), date(2026, 3, 31)


@pytest.mark.parametrize(
    ("text", "unit", "expected"),
    [
        ("1,234.56", "crore", 1234.56),
        ("(1,234.56)", "lakh", -12.3456),
        ("500", "million", 50.0),
        ("abc", "crore", None),
    ],
)
def test_parse_amount(text: str, unit: str, expected: float | None) -> None:
    assert parse_amount(text, unit) == (pytest.approx(expected) if expected is not None else None)


def test_parse_amount_unknown_unit() -> None:
    assert parse_amount("100", "unknown") is None


def test_amount_must_appear_in_quote() -> None:
    assert amount_in_quote("1,234.50", "Sale of goods to XYZ Ltd 1234.50 (previous year 980.00)")
    assert not amount_in_quote("9,999", "Sale of goods 1,234.50")


def _passage(text: str) -> dict[str, Passage]:
    return {"P1": Passage("P1", "c", "doc-1", "Annual report", "annual_report", 12, text)}


def test_verify_quote_ignores_case_and_whitespace() -> None:
    passages = _passage("The company commissioned a 500 MW\nsolar plant in Gujarat.")
    assert verify_quote(passages, "P1", "commissioned a 500 MW solar   plant") is not None
    assert verify_quote(passages, "P1", "commissioned a 900 MW wind farm") is None
    assert verify_quote(passages, "P2", "commissioned a 500 MW solar plant") is None
    assert verify_quote(passages, "P1", "500 MW") is None  # too short to count as evidence


def test_debt_profile() -> None:
    fy = FactTable()
    for (metric, period), value in {
        ("total_debt", FY25): 100.0,
        ("total_debt", FY26): 300.0,
        ("cash_and_short_term_investments", FY26): 50.0,
        ("equity", FY26): 600.0,
        ("ebitda", FY26): 150.0,
        ("ebit", FY26): 90.0,
        ("interest_expense", FY26): 30.0,
        ("short_term_debt", FY26): 60.0,
        ("current_debt", FY26): 15.0,
    }.items():
        fy.values[(metric, period)] = value
    latest = debt_profile(fy)[-1]
    assert latest.net_debt == 250
    assert latest.debt_to_equity == pytest.approx(0.5)
    assert latest.debt_to_ebitda == pytest.approx(2.0)
    assert latest.interest_coverage == pytest.approx(3.0)
    assert latest.implied_interest_rate == pytest.approx(30 / 200)
    assert latest.short_term_share == pytest.approx(0.25)


def _row(name: str, subject: bool, **values: float | None) -> CompanyRow:
    return CompanyRow(name, name, name, subject, FY26, dict(values), ())


def test_compare_ranks_and_medians() -> None:
    subject = _row("S", True, net_margin=0.10, debt_to_equity=0.5)
    peers = [
        _row("A", False, net_margin=0.05, debt_to_equity=1.0),
        _row("B", False, net_margin=0.20, debt_to_equity=0.2),
        _row("C", False, net_margin=0.08, debt_to_equity=0.8),
    ]
    result = compare(subject, peers)
    assert result.peer_median["net_margin"] == pytest.approx(0.08)
    assert result.subject_rank["net_margin"] == 2
    assert result.better_than_median["net_margin"] is True
    assert result.subject_rank["debt_to_equity"] == 2  # lower is better
    assert result.better_than_median["debt_to_equity"] is True
    assert result.subject_rank["roce"] is None


def test_red_flags_ordered_by_severity() -> None:
    flags = draft_red_flags(
        {
            "financial_warnings": {
                "results": [
                    {"check": "debt", "status": "watch", "explanation": "D/E"},
                    {"check": "roce", "status": "flag", "explanation": "RoCE"},
                    {"check": "dilution", "status": "clear", "explanation": "-"},
                ]
            },
            "growth_analysis": {"years": [{"net_margin": -0.1, "revenue_growth": 0.2}]},
            "debt_structure": {"years": [{"interest_coverage": 0.8, "debt_to_ebitda": 5.0}]},
        }
    )
    titles = [f.title for f in flags]
    assert titles[:3] == ["Low return on capital", "Loss-making", "Thin interest cover"]
    assert "Shareholder dilution" not in titles
    assert [f.severity for f in flags] == sorted(
        (f.severity for f in flags), key=["high", "medium", "low"].index
    )


def test_local_store_is_write_once_and_sandboxed(tmp_path: Path) -> None:
    store = LocalStore(tmp_path)
    store.put("documents/x.pdf", b"one", "application/pdf")
    store.put("documents/x.pdf", b"two", "application/pdf")
    assert store.get("documents/x.pdf") == b"one"
    with pytest.raises(ValueError):
        store.put("../escape.pdf", b"x", "application/pdf")


def test_revenue_is_ranked_but_not_judged() -> None:
    result = compare(
        _row("S", True, revenue=10.0), [_row("A", False, revenue=50.0), _row("B", False, revenue=5.0)]
    )
    assert result.subject_rank["revenue"] == 2
    assert result.better_than_median["revenue"] is None


def test_red_flag_states_the_actual_figure() -> None:
    [flag] = draft_red_flags(
        {
            "financial_warnings": {
                "results": [
                    {
                        "check": "working_capital",
                        "status": "flag",
                        "value": 355.7,
                        "inputs": {},
                        "explanation": "CCC",
                    }
                ]
            }
        }
    )
    assert flag.explanation.startswith("Cash conversion cycle of 356 days")
