import type { FinancialFact } from '../companies/api'

const SECTIONS: { title: string; metrics: string[] }[] = [
  {
    title: 'Income statement',
    metrics: [
      'revenue',
      'cost_of_revenue',
      'gross_profit',
      'operating_expenses',
      'total_expenses',
      'ebitda',
      'depreciation_amortization',
      'ebit',
      'interest_expense',
      'interest_investment_income',
      'other_income',
      'profit_before_tax',
      'net_profit',
      'eps_basic',
      'weighted_shares_basic',
    ],
  },
  {
    title: 'Balance sheet',
    metrics: [
      'cash_and_equivalents',
      'short_term_investments',
      'cash_and_short_term_investments',
      'receivables',
      'inventory',
      'total_current_assets',
      'property_plant_equipment',
      'total_assets',
      'accounts_payable',
      'current_debt',
      'long_term_debt',
      'total_debt',
      'total_current_liabilities',
      'total_liabilities',
      'equity',
      'shares_outstanding',
    ],
  },
  {
    title: 'Cash flow',
    metrics: [
      'operating_cash_flow',
      'capex',
      'investing_cash_flow',
      'debt_issued',
      'debt_repaid',
      'equity_issued',
      'financing_cash_flow',
      'net_cash_flow',
      'free_cash_flow',
    ],
  },
  {
    title: 'Shareholding',
    metrics: [
      'promoter_holding_pct',
      'fii_holding_pct',
      'dii_holding_pct',
      'public_holding_pct',
      'shareholder_count',
    ],
  },
]

export const METRIC_LABELS: Record<string, string> = {
  depreciation_amortization: 'Depreciation & amortization',
  interest_investment_income: 'Interest & investment income',
  property_plant_equipment: 'Property, plant & equipment',
  short_term_investments: 'Short-term investments',
  cash_and_short_term_investments: 'Cash & short-term investments',
  cash_and_equivalents: 'Cash & equivalents',
  long_term_debt: 'Long-term debt',
  weighted_shares_basic: 'Weighted shares (basic)',
  ebitda: 'EBITDA',
  ebit: 'EBIT',
  eps_basic: 'EPS (basic)',
  capex: 'Capex',
  fii_holding_pct: 'FII holding',
  dii_holding_pct: 'DII holding',
  promoter_holding_pct: 'Promoter holding',
  public_holding_pct: 'Public holding',
}

export type Row = { metric: string; unit: string; values: Map<string, number>; sourceIds: string[] }

export function pivotFacts(facts: FinancialFact[]) {
  const periods = [...new Set(facts.map((f) => f.period_end))].sort()
  const rows = new Map<string, Row>()
  for (const f of facts) {
    const row: Row = rows.get(f.metric) ?? {
      metric: f.metric,
      unit: f.unit,
      values: new Map(),
      sourceIds: [],
    }
    row.values.set(f.period_end, f.value)
    if (f.source_document_id && !row.sourceIds.includes(f.source_document_id))
      row.sourceIds.push(f.source_document_id)
    rows.set(f.metric, row)
  }
  const known = new Set(SECTIONS.flatMap((s) => s.metrics))
  const sections = [
    ...SECTIONS.map((s) => ({ title: s.title, rows: s.metrics.flatMap((m) => rows.get(m) ?? []) })),
    { title: 'Other', rows: [...rows.values()].filter((r) => !known.has(r.metric)) },
  ].filter((s) => s.rows.length > 0)
  return { periods, sections }
}
