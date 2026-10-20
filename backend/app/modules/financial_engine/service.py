from app.modules.financial_engine import warnings as w
from app.schemas.warnings import WarningInputs


def run_all_checks(i: WarningInputs) -> list[w.WarningResult]:
    return [
        w.debt_check(i.total_debt, i.equity),
        w.working_capital_check(i.receivable_days, i.inventory_days, i.payable_days),
        w.operating_cash_flow_check(i.cumulative_ocf, i.cumulative_net_profit),
        w.promoter_check(i.pledged_pct_of_promoter, i.promoter_holding_change_pp),
        w.rpt_check(i.rpt_value, i.revenue),
        w.dilution_check(i.shares_start, i.shares_end),
        w.tax_dividend_check(i.effective_tax_rate, i.payout_ratio),
        w.roce_check(i.roce),
    ]
