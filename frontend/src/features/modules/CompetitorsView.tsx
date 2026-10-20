import { Link } from 'react-router'
import { cn } from '@/lib/cn'
import { fiscalYear, formatCr, formatMultiple, formatPct } from '@/lib/format'
import type { CompetitorsData } from './schemas'

function format(key: string, value: number | null | undefined) {
  if (key === 'revenue') return formatCr(value)
  if (key === 'debt_to_equity' || key === 'ocf_to_profit') return formatMultiple(value)
  return formatPct(value, { signed: key === 'revenue_growth' })
}

export function CompetitorsView({ data }: { data: CompetitorsData }) {
  const total = data.companies.length
  return (
    <div className="space-y-3">
      <div className="overflow-x-auto">
        <table className="w-full text-sm tabular-nums">
          <thead className="text-xs tracking-wide text-slate-500 uppercase">
            <tr className="border-b border-slate-200">
              <th className="sticky left-0 bg-white py-2 pr-4 text-left font-medium">Company</th>
              <th className="py-2 pr-4 text-left font-medium">Year</th>
              {data.metrics.map((m) => (
                <th key={m.key} className="py-2 pr-4 text-right font-medium whitespace-nowrap">
                  {m.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.companies.map((c) => (
              <tr
                key={c.company_id}
                className={cn(
                  'border-b border-slate-100',
                  c.is_subject && 'bg-indigo-50/60 font-medium',
                )}
              >
                <td
                  className={cn(
                    'sticky left-0 py-2 pr-4 whitespace-nowrap',
                    c.is_subject ? 'bg-indigo-50' : 'bg-white',
                  )}
                >
                  {c.is_subject ? c.name : <span title={c.nse_symbol ?? ''}>{c.name}</span>}
                </td>
                <td className="py-2 pr-4">{c.period_end ? fiscalYear(c.period_end) : '—'}</td>
                {data.metrics.map((m) => (
                  <td key={m.key} className="py-2 pr-4 text-right whitespace-nowrap">
                    {format(m.key, c.values[m.key])}
                  </td>
                ))}
              </tr>
            ))}
            <tr className="border-t-2 border-slate-200 text-slate-600">
              <td className="sticky left-0 bg-white py-2 pr-4">Peer median</td>
              <td />
              {data.metrics.map((m) => (
                <td key={m.key} className="py-2 pr-4 text-right">
                  {format(m.key, m.peer_median)}
                </td>
              ))}
            </tr>
            <tr className="text-slate-600">
              <td className="sticky left-0 bg-white py-2 pr-4">Rank (of {total})</td>
              <td />
              {data.metrics.map((m) => (
                <td
                  key={m.key}
                  className={cn(
                    'py-2 pr-4 text-right',
                    m.better_than_median === true && 'text-emerald-700',
                    m.better_than_median === false && 'text-red-700',
                  )}
                >
                  {m.rank ?? '—'}
                  {m.better_than_median != null && (m.better_than_median ? ' ▲' : ' ▼')}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
      <p className="text-xs text-slate-500">
        ▲ better / ▼ worse than the peer median (for debt/equity, lower is better). Peer figures are
        consolidated and from secondary sources; groups with lending arms (e.g. TVS Motor, Bajaj
        Auto) carry their loan books in debt and interest, so compare those ratios with care. Peers
        can be opened from the{' '}
        <Link to="/?peers=1" className="text-indigo-700 hover:underline">
          company list
        </Link>
        .
      </p>
    </div>
  )
}
