import {
  fiscalYear,
  formatByUnit,
  formatCr,
  formatPct,
  humanize,
  niceTicks,
  quarterLabel,
} from './format'

describe('format', () => {
  it('formats crore with Indian grouping', () => {
    expect(formatCr(3671.8)).toBe('₹3,671.8 Cr')
    expect(formatCr(123456.7)).toBe('₹1,23,456.7 Cr')
    expect(formatCr(-956.41)).toBe('−₹956.4 Cr')
    expect(formatCr(null)).toBe('—')
  })

  it('formats percentages', () => {
    expect(formatPct(0.2721)).toBe('27.2%')
    expect(formatPct(0.628, { signed: true })).toBe('+62.8%')
    expect(formatPct(-0.141, { signed: true })).toBe('-14.1%')
  })

  it('maps period ends to Indian fiscal years and quarters', () => {
    expect(fiscalYear('2026-03-31')).toBe('FY2026')
    expect(fiscalYear('2025-06-30')).toBe('FY2026')
    expect(quarterLabel('2026-06-30')).toBe('Jun 2026')
  })

  it('formats by unit', () => {
    expect(formatByUnit(40.72, 'PCT')).toBe('40.72%')
    expect(formatByUnit(229896, 'COUNT')).toBe('2,29,896')
    expect(formatByUnit(-13.99, 'INR')).toBe('−₹13.99')
  })

  it('humanizes keys with acronyms', () => {
    expect(humanize('cumulative_ocf')).toBe('Cumulative OCF')
    expect(humanize('roce')).toBe('RoCE')
  })

  it('builds round axis ticks', () => {
    expect(niceTicks(3671.8)).toEqual([0, 1000, 2000, 3000, 4000])
    expect(niceTicks(0)).toEqual([0])
  })
})
