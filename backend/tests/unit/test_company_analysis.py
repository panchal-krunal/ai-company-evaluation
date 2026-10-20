from datetime import date

import pytest

from app.modules.financial_engine.company_analysis import FactTable, analyse_growth, evaluate_warnings
from app.modules.financial_engine.warnings import (
    WarningCheck,
    WarningStatus,
    operating_cash_flow_check,
)

FY24, FY25, FY26 = date(2024, 3, 31), date(2025, 3, 31), date(2026, 3, 31)


def _table(data: dict[str, dict[date, float]]) -> FactTable:
    table = FactTable()
    for metric, series in data.items():
        for period, value in series.items():
            table.values[(metric, period)] = value
            table.sources[(metric, period)] = "src-1"
    return table


@pytest.fixture
def loss_making_fy() -> FactTable:
    return _table(
        {
            "revenue": {FY24: 1000, FY25: 1200, FY26: 1500},
            "cost_of_revenue": {FY26: 1200},
            "gross_profit": {FY24: 100, FY25: 150, FY26: 300},
            "net_profit": {FY24: -300, FY25: -200, FY26: -100},
            "profit_before_tax": {FY26: -100},
            "operating_cash_flow": {FY24: -150, FY25: -100, FY26: 20},
            "total_debt": {FY26: 300},
            "equity": {FY26: 1000},
            "receivables": {FY26: 30},
            "inventory": {FY26: 120},
            "accounts_payable": {FY26: 240},
            "shares_outstanding": {FY25: 100, FY26: 125},
            "ebit": {FY26: -90},
            "total_assets": {FY26: 2000},
            "total_current_liabilities": {FY26: 500},
        }
    )


def _by_check(results: list) -> dict:  # type: ignore[type-arg]
    return {r.check: r for r in results}


def test_loss_making_company(loss_making_fy: FactTable) -> None:
    as_of, results = evaluate_warnings(loss_making_fy, FactTable())
    r = _by_check(results)
    assert as_of == FY26
    assert len(results) == 8

    assert r[WarningCheck.DEBT].status is WarningStatus.CLEAR
    assert r[WarningCheck.DEBT].value == pytest.approx(0.3)

    # CCC = 30/1500*365 + 120/1200*365 - 240/1200*365 = 7.3 + 36.5 - 73 = -29.2 days
    assert r[WarningCheck.WORKING_CAPITAL].value == pytest.approx(-29.2)
    assert r[WarningCheck.WORKING_CAPITAL].status is WarningStatus.CLEAR

    # Losses over the window and cumulative OCF of -230: flagged, ratio not computed
    ocf = r[WarningCheck.OPERATING_CASH_FLOW]
    assert ocf.status is WarningStatus.FLAG
    assert ocf.value is None
    assert ocf.inputs["cumulative_ocf"] == pytest.approx(-230)

    assert r[WarningCheck.DILUTION].value == pytest.approx(0.25)
    assert r[WarningCheck.DILUTION].status is WarningStatus.FLAG

    # RoCE = -90 / (2000 - 500) = -6%
    assert r[WarningCheck.ROCE].value == pytest.approx(-0.06)
    assert r[WarningCheck.ROCE].status is WarningStatus.FLAG

    for missing in (WarningCheck.PROMOTER_HOLDING, WarningCheck.RPT, WarningCheck.TAX_DIVIDEND):
        assert r[missing].status is WarningStatus.NOT_ASSESSED

    assert r[WarningCheck.DEBT].source_document_ids == ("src-1",)


def test_promoter_holding_change_reported_without_pledge_data(loss_making_fy: FactTable) -> None:
    quarterly = _table({"promoter_holding_pct": {date(2025, 6, 30): 42.0, date(2026, 6, 30): 40.5}})
    _, results = evaluate_warnings(loss_making_fy, quarterly)
    promoter = _by_check(results)[WarningCheck.PROMOTER_HOLDING]
    assert promoter.status is WarningStatus.NOT_ASSESSED
    assert promoter.inputs["promoter_holding_change_pp"] == pytest.approx(-1.5)


def test_no_revenue_raises() -> None:
    with pytest.raises(ValueError, match="No annual revenue"):
        evaluate_warnings(FactTable(), FactTable())


def test_ocf_check_profitable_and_positive_cash_despite_losses() -> None:
    assert operating_cash_flow_check(90, 100).status is WarningStatus.CLEAR
    assert operating_cash_flow_check(10, -50).status is WarningStatus.WATCH


def test_growth(loss_making_fy: FactTable) -> None:
    g = analyse_growth(loss_making_fy)
    assert g.full_period_years == 2
    assert g.revenue_cagr_full == pytest.approx((1500 / 1000) ** 0.5 - 1)
    assert g.revenue_cagr_3y is None  # needs four year-ends
    assert g.years[-1].revenue_growth == pytest.approx(0.25)
    assert g.years[-1].gross_margin == pytest.approx(0.2)
    assert g.years[0].revenue_growth is None
