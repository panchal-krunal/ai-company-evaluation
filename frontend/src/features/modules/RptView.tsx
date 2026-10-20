import { formatCr } from '@/lib/format'
import { ClaimList, EvidenceQuote } from './Evidence'
import type { RptData } from './schemas'

export function RptView({ data }: { data: RptData }) {
  const current = data.lines.filter((l) => l.year === 'current')
  return (
    <div className="space-y-6">
      <dl className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {[
          ['Transactions, latest year', data.total_transactions_current_cr],
          ['Transactions, previous year', data.total_transactions_previous_cr],
          ['Closing balances', data.total_balances_current_cr],
        ].map(([label, value]) => (
          <div key={label as string} className="rounded-md border border-slate-200 px-4 py-3">
            <dt className="text-xs text-slate-500">{label}</dt>
            <dd className="mt-1 text-lg font-semibold">{formatCr(value as number | null)}</dd>
          </div>
        ))}
      </dl>
      {data.unverified_lines > 0 && (
        <p className="text-xs text-amber-800">
          {data.unverified_lines} line(s) excluded from totals because the printed amount was not
          found in the quote.
        </p>
      )}
      {data.top_parties.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-semibold">Largest counterparties (latest year)</h3>
          <ul className="divide-y divide-slate-100 text-sm">
            {data.top_parties.map((p) => (
              <li key={p.related_party} className="flex justify-between py-1.5">
                <span>{p.related_party}</span>
                <span className="tabular-nums">{formatCr(p.amount_cr)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      <div>
        <h3 className="mb-2 text-sm font-semibold">Latest-year lines ({current.length})</h3>
        <ul className="divide-y divide-slate-100">
          {current.map((l, i) => (
            <li key={i} className="space-y-1 py-3 text-sm">
              <div className="flex flex-wrap justify-between gap-2">
                <span>
                  <span className="font-medium">{l.related_party}</span>{' '}
                  <span className="text-slate-500">
                    ({l.relationship}) · {l.nature} · {l.kind.replace('_', ' ')}
                  </span>
                </span>
                <span className="tabular-nums">
                  {l.amount_cr != null
                    ? formatCr(l.amount_cr)
                    : `${l.amount_as_reported} ${l.unit_as_reported} (unverified)`}
                </span>
              </div>
              <EvidenceQuote item={l.evidence} />
            </li>
          ))}
        </ul>
      </div>
      {data.observations.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-semibold">Observations</h3>
          <ClaimList claims={data.observations} />
        </div>
      )}
    </div>
  )
}
