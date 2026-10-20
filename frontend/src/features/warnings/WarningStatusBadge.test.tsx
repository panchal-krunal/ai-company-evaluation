import { render, screen } from '@testing-library/react'
import { WarningStatusBadge } from './WarningStatusBadge'

describe('WarningStatusBadge', () => {
  it('renders the status label', () => {
    render(<WarningStatusBadge status="flag" />)
    expect(screen.getByText('Flag')).toBeInTheDocument()
  })

  it('labels checks that could not be assessed', () => {
    render(<WarningStatusBadge status="not_assessed" />)
    expect(screen.getByText('Not assessed')).toBeInTheDocument()
  })
})
