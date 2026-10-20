import { render, screen } from '@testing-library/react'
import type { Source } from '@/lib/sources'
import type { WarningResult } from './api'
import { WarningsTable } from './WarningsTable'

const source: Source = {
  id: 'src-1',
  title: 'Balance sheet',
  url: 'https://example.com/bs',
  publisher: 'stockanalysis.com',
  isPrimary: false,
}

const results: WarningResult[] = [
  {
    check: 'debt',
    status: 'clear',
    value: 0.2582,
    explanation: 'Debt-to-equity ratio.',
    inputs: { total_debt: 664.2, equity: 2572.6 },
    source_document_ids: ['src-1'],
  },
  {
    check: 'related_party_transactions',
    status: 'not_assessed',
    value: null,
    explanation: 'Related-party transaction data not loaded yet.',
    inputs: {},
    source_document_ids: [],
  },
]

describe('WarningsTable', () => {
  it('shows each check with its status, formatted value, inputs and source', () => {
    render(<WarningsTable results={results} sources={new Map([['src-1', source]])} />)
    expect(screen.getByText('Debt')).toBeInTheDocument()
    expect(screen.getByText('0.26× D/E')).toBeInTheDocument()
    expect(screen.getByText('₹2,572.6 Cr')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /stockanalysis.com/ })).toHaveAttribute(
      'href',
      'https://example.com/bs',
    )
    expect(screen.getByText('Secondary')).toBeInTheDocument()
    expect(screen.getByText('Not assessed')).toBeInTheDocument()
  })
})
