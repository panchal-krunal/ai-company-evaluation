import pytest

from app.modules.financial_engine.metrics import cagr, cash_conversion, margin, yoy_growth


def test_cagr_doubles_over_five_years() -> None:
    assert cagr(100, 200, 5) == pytest.approx(0.1487, abs=1e-4)


@pytest.mark.parametrize(("start", "end", "years"), [(0, 100, 5), (100, -5, 5), (100, 200, 0)])
def test_cagr_undefined(start: float, end: float, years: float) -> None:
    assert cagr(start, end, years) is None


def test_margin_and_zero_revenue() -> None:
    assert margin(20, 100) == pytest.approx(0.2)
    assert margin(20, 0) is None


def test_yoy_growth() -> None:
    assert yoy_growth([100, 110, 99]) == pytest.approx([0.10, -0.10])


def test_cash_conversion() -> None:
    assert cash_conversion(80, 100) == pytest.approx(0.8)
