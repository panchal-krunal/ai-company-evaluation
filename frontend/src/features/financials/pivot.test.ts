import type { FinancialFact } from '../companies/api'
import { pivotFacts } from './pivot'

const fact = (metric: string, period_end: string, value: number): FinancialFact => ({
  metric,
  period_end,
  period_type: 'FY',
  basis: 'consolidated',
  value,
  unit: 'INR_CR',
  source_document_id: 's1',
})

describe('pivotFacts', () => {
  it('groups metrics into statement sections with sorted periods', () => {
    const { periods, sections } = pivotFacts([
      fact('total_debt', '2026-03-31', 664.2),
      fact('revenue', '2026-03-31', 3671.8),
      fact('revenue', '2025-03-31', 2255),
      fact('custom_metric', '2026-03-31', 1),
    ])
    expect(periods).toEqual(['2025-03-31', '2026-03-31'])
    expect(sections.map((s) => s.title)).toEqual(['Income statement', 'Balance sheet', 'Other'])
    expect(sections[0]?.rows[0]?.values.get('2025-03-31')).toBe(2255)
    expect(sections[0]?.rows[0]?.sourceIds).toEqual(['s1'])
  })
})
