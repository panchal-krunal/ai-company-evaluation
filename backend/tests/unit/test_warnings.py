from app.modules.financial_engine.warnings import (
    WarningStatus,
    debt_check,
    operating_cash_flow_check,
    roce_check,
)


def test_debt_boundaries() -> None:
    assert debt_check(50, 100).status is WarningStatus.CLEAR
    assert debt_check(100, 100).status is WarningStatus.WATCH
    assert debt_check(200, 100).status is WarningStatus.FLAG


def test_zero_equity_is_watch_not_crash() -> None:
    result = debt_check(100, 0)
    assert result.value is None
    assert result.status is WarningStatus.WATCH


def test_low_cash_conversion_flags() -> None:
    assert operating_cash_flow_check(40, 100).status is WarningStatus.FLAG


def test_roce_lower_is_worse() -> None:
    assert roce_check(0.20).status is WarningStatus.CLEAR
    assert roce_check(0.10).status is WarningStatus.WATCH
    assert roce_check(0.05).status is WarningStatus.FLAG
