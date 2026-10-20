import { SourceLinks } from '@/components/ui/SourceLinks'
import { formatCr, formatDays, formatMultiple, formatPct, humanize } from '@/lib/format'
import type { Source } from '@/lib/sources'
import type { WarningResult } from './api'
import { WarningStatusBadge, type WarningStatus } from './WarningStatusBadge'

const CHECKS: Record<string, { label: string; format: (v: number) => string }> = {
  debt: { label: 'Debt', format: (v) => `${formatMultiple(v)} D/E` },
  working_capital: { label: 'Working capital', format: (v) => `${formatDays(v)} CCC` },
  operating_cash_flow: {
    label: 'Operating cash flow',
    format: (v) => `${formatMultiple(v)} OCF/profit`,
  },
  promoter_holding_pledging: {
    label: 'Promoter holding & pledging',
    format: (v) => `${formatPct(v)} pledged`,
  },
  related_party_transactions: {
    label: 'Related-party transactions',
    format: (v) => `${formatPct(v)} of revenue`,
  },
  dilution: { label: 'Dilution', format: (v) => `${formatPct(v, { signed: true })} shares` },
  tax_dividend: { label: 'Tax & dividend', format: (v) => `${formatPct(v)} tax rate` },
  roce: { label: 'RoCE', format: (v) => formatPct(v) },
}

const STATUS_ORDER: WarningStatus[] = ['flag', 'watch', 'clear', 'not_assessed']

function formatInput(key: string, value: number | null): string {
  if (value == null) return '—'
  if (key.endsWith('_days')) return formatDays(value)
  if (key.endsWith('_pp')) return `${value > 0 ? '+' : ''}${value.toFixed(2)} pp`
  if (['roce', 'effective_tax_rate', 'payout_ratio', 'pledged_pct_of_promoter'].includes(key))
    return formatPct(value)
  if (key.startsWith('shares_')) return `${value.toFixed(2)} Mn`
  return formatCr(value)
}

export function WarningSummary({ results }: { results: WarningResult[] }) {
  return (
    <div className="flex flex-wrap gap-2" aria-label="Warning summary">
      {STATUS_ORDER.map((status) => {
        const count = results.filter((r) => r.status === status).length
        return count > 0 ? (
          <span key={status} className="inline-flex items-center gap-1.5 text-sm">
            <WarningStatusBadge status={status} />
            <span className="font-semibold">{count}</span>
          </span>
        ) : null
      })}
    </div>
  )
}

export function WarningsTable({
  results,
  sources,
}: {
  results: WarningResult[]
  sources: Map<string, Source>
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="text-left text-xs tracking-wide text-slate-500 uppercase">
          <tr className="border-b border-slate-200">
            <th className="py-2 pr-4 font-medium">Check</th>
            <th className="py-2 pr-4 font-medium">Status</th>
            <th className="py-2 pr-4 font-medium">Value</th>
            <th className="py-2 font-medium">Detail</th>
          </tr>
        </thead>
        <tbody>
          {results.map((r) => {
            const check = CHECKS[r.check] ?? {
              label: humanize(r.check),
              format: (v: number) => v.toFixed(2),
            }
            const inputs = Object.entries(r.inputs)
            return (
              <tr key={r.check} className="border-b border-slate-100 align-top last:border-0">
                <td className="py-3 pr-4 font-medium whitespace-nowrap">{check.label}</td>
                <td className="py-3 pr-4">
                  <WarningStatusBadge status={r.status} />
                </td>
                <td className="py-3 pr-4 whitespace-nowrap tabular-nums">
                  {r.value == null ? '—' : check.format(r.value)}
                </td>
                <td className="space-y-1.5 py-3">
                  <p>{r.explanation}</p>
                  {inputs.length > 0 && (
                    <dl className="flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-slate-500">
                      {inputs.map(([key, value]) => (
                        <div key={key} className="flex gap-1">
                          <dt>{humanize(key)}:</dt>
                          <dd className="text-slate-700 tabular-nums">{formatInput(key, value)}</dd>
                        </div>
                      ))}
                    </dl>
                  )}
                  <SourceLinks ids={r.source_document_ids} sources={sources} />
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
