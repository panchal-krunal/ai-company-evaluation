import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { CompetitorsView } from './CompetitorsView'

describe('CompetitorsView', () => {
  it('shows subject, peers, median and rank', () => {
    render(
      <MemoryRouter>
        <CompetitorsView
          data={{
            metrics: [
              {
                key: 'net_margin',
                label: 'Net margin',
                higher_is_better: true,
                subject: 0.3,
                peer_median: 0.12,
                rank: 1,
                better_than_median: true,
              },
            ],
            companies: [
              {
                company_id: '1',
                name: 'Cupid Ltd',
                nse_symbol: 'CUPID',
                is_subject: true,
                period_end: '2026-03-31',
                values: { net_margin: 0.3 },
              },
              {
                company_id: '2',
                name: 'Emami Ltd',
                nse_symbol: 'EMAMILTD',
                is_subject: false,
                period_end: '2026-03-31',
                values: { net_margin: 0.2 },
              },
            ],
          }}
        />
      </MemoryRouter>,
    )
    expect(screen.getByText('Cupid Ltd')).toBeInTheDocument()
    expect(screen.getByText('12.0%')).toBeInTheDocument()
    expect(screen.getByText('1 ▲')).toBeInTheDocument()
    expect(screen.getByText('Rank (of 2)')).toBeInTheDocument()
  })
})
