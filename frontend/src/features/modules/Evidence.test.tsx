import { render, screen } from '@testing-library/react'
import { ClaimList } from './Evidence'
import type { ClaimItem } from './schemas'

const claims: ClaimItem[] = [
  {
    statement: 'Plant capacity doubles in FY27',
    topic: 'Capacity',
    sentiment: 'positive',
    supported: true,
    evidence: [
      {
        passage_id: 'P1',
        quote: 'capacity will double by FY27',
        verified: true,
        source_document_id: 'doc-1',
        document_title: 'Annual Report FY2026',
        page_number: 42,
      },
    ],
  },
  {
    statement: 'Market share is 40%',
    topic: 'Market',
    sentiment: 'neutral',
    supported: false,
    evidence: [
      {
        passage_id: 'P2',
        quote: 'invented sentence',
        verified: false,
        source_document_id: null,
        document_title: null,
        page_number: null,
      },
    ],
  },
]

describe('ClaimList', () => {
  it('links verified evidence to the cited page and flags unsupported claims', () => {
    render(<ClaimList claims={claims} />)
    expect(screen.getByRole('link', { name: /Annual Report FY2026, p\.42/ })).toHaveAttribute(
      'href',
      '/api/v1/documents/doc-1/file#page=42',
    )
    expect(screen.getByText('Unsupported — do not rely on this')).toBeInTheDocument()
    expect(screen.getByText('Quote not found in the cited passage')).toBeInTheDocument()
  })
})
