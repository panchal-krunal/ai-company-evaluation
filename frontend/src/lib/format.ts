const crore = new Intl.NumberFormat('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
const integer = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 })
const twoDp = new Intl.NumberFormat('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

export const DASH = '—'

/** ₹ crore, Indian digit grouping: 3,671.8 → "₹3,671.8 Cr". */
export function formatCr(value: number | null | undefined): string {
  if (value == null) return DASH
  return `${value < 0 ? '−' : ''}₹${crore.format(Math.abs(value))} Cr`
}

/** A ratio as a percentage: 0.2721 → "27.2%". */
export function formatPct(value: number | null | undefined, { signed = false } = {}): string {
  if (value == null) return DASH
  const pct = value * 100
  return `${signed && pct > 0 ? '+' : ''}${pct.toFixed(1)}%`
}

export function formatDays(value: number | null | undefined): string {
  return value == null ? DASH : `${integer.format(value)} days`
}

export function formatMultiple(value: number | null | undefined): string {
  return value == null ? DASH : `${value.toFixed(2)}×`
}

/** Format a stored figure by its unit code from the backend. */
export function formatByUnit(value: number | null | undefined, unit: string): string {
  if (value == null) return DASH
  switch (unit) {
    case 'INR_CR':
      return crore.format(value)
    case 'INR':
      return `${value < 0 ? '−' : ''}₹${twoDp.format(Math.abs(value))}`
    case 'PCT':
      return `${value.toFixed(2)}%`
    case 'SHARES_MN':
      return `${twoDp.format(value)} Mn`
    case 'COUNT':
      return integer.format(value)
    default:
      return String(value)
  }
}

export const UNIT_LABELS: Record<string, string> = {
  INR_CR: '₹ Cr',
  INR: '₹',
  PCT: '%',
  SHARES_MN: 'Mn shares',
  COUNT: 'count',
}

/** Indian fiscal years end on 31 March: "2026-03-31" → "FY2026". */
export function fiscalYear(periodEnd: string): string {
  const [year, month] = periodEnd.split('-').map(Number)
  if (year === undefined || month === undefined) return periodEnd
  return `FY${month <= 3 ? year : year + 1}`
}

/** "2026-06-30" → "Jun 2026". */
export function quarterLabel(periodEnd: string): string {
  const date = new Date(`${periodEnd}T00:00:00Z`)
  return date.toLocaleDateString('en-IN', { month: 'short', year: 'numeric', timeZone: 'UTC' })
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
}

const ACRONYMS: Record<string, string> = {
  ocf: 'OCF',
  roce: 'RoCE',
  ebit: 'EBIT',
  ebitda: 'EBITDA',
  eps: 'EPS',
  rpt: 'RPT',
  pp: 'pp',
  pct: '%',
  fii: 'FII',
  dii: 'DII',
}

/** "cumulative_ocf" → "Cumulative OCF". */
export function humanize(key: string): string {
  const words = key.split('_').map((w) => ACRONYMS[w] ?? w)
  const text = words.join(' ')
  return text.charAt(0).toUpperCase() + text.slice(1)
}

/** Round axis ticks from 0 to just above `max`, e.g. 3,672 → [0, 1000, 2000, 3000, 4000]. */
export function niceTicks(max: number, count = 4): number[] {
  if (!(max > 0)) return [0]
  const rough = max / count
  const magnitude = 10 ** Math.floor(Math.log10(rough))
  const step = [1, 2, 2.5, 5, 10].map((m) => m * magnitude).find((s) => s >= rough) ?? rough
  return Array.from({ length: Math.ceil(max / step) + 1 }, (_, i) => i * step)
}
