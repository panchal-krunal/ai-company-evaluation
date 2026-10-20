import { fiscalYear, formatCr, formatMultiple, formatPct } from '@/lib/format'
import { ClaimList, EvidenceQuote } from './Evidence'
import type { DebtData } from './schemas'

export function DebtView({ data }: { data: DebtData }) {
  const latestDebt = data.years.at(-1)?.total_debt
  return (
    <div className="space-y-6">
      <div className="overflow-x-auto">
        <table className="w-full text-sm tabular-nums">
          <caption className="mb-2 text-left text-sm font-semibold">
            Debt metrics (from stored figures)
          </caption>
          <thead className="text-xs tracking-wide text-slate-500 uppercase">
            <tr className="border-b border-slate-200">
              {[
                'Year',
                'Total debt',
                'Net debt (− = net cash)',
                'Debt/equity',
                'Debt/EBITDA',
                'Interest cover',
                'Implied rate',
                'Short-term share',
              ].map((h, i) => (
                <th key={h} className={`py-2 pr-4 font-medium ${i ? 'text-right' : 'text-left'}`}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.years.map((y) => (
              <tr key={y.period_end} className="border-b border-slate-100 last:border-0">
                <td className="py-2 pr-4">{fiscalYear(y.period_end)}</td>
                <td className="py-2 pr-4 text-right">{formatCr(y.total_debt)}</td>
                <td className="py-2 pr-4 text-right">{formatCr(y.net_debt)}</td>
                <td className="py-2 pr-4 text-right">{formatMultiple(y.debt_to_equity)}</td>
                <td className="py-2 pr-4 text-right">{formatMultiple(y.debt_to_ebitda)}</td>
                <td className="py-2 pr-4 text-right">{formatMultiple(y.interest_coverage)}</td>
                <td className="py-2 pr-4 text-right">{formatPct(y.implied_interest_rate)}</td>
                <td className="py-2 text-right">{formatPct(y.short_term_share)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data.borrowings === null ? (
        <p className="text-sm text-slate-500">
          Borrowing-level detail appears here after the AI extraction runs.
        </p>
      ) : (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold">Borrowings extracted from the annual report</h3>
          <p className="text-xs text-slate-500">
            Extracted total {formatCr(data.extracted_total_cr)} vs stored total debt{' '}
            {formatCr(latestDebt)} · secured share {formatPct(data.secured_share)}. Amounts count
            only when the printed figure appears in the quoted text.
          </p>
          <ul className="divide-y divide-slate-100">
            {data.borrowings.map((b, i) => (
              <li key={i} className="space-y-1 py-3 text-sm">
                <div className="flex flex-wrap justify-between gap-2">
                  <span className="font-medium">
                    {b.lender_or_instrument} · {b.facility_type}
                  </span>
                  <span className="tabular-nums">
                    {b.amount_cr != null
                      ? formatCr(b.amount_cr)
                      : `${b.amount_as_reported ?? '—'} ${b.unit_as_reported} (unverified)`}
                  </span>
                </div>
                <p className="text-xs text-slate-500">
                  {b.secured == null ? 'Security not stated' : b.secured ? 'Secured' : 'Unsecured'}{' '}
                  · {b.maturity.replace('_', '-')}
                  {b.interest_rate && ` · ${b.interest_rate}`}
                  {b.repayment_terms && ` · ${b.repayment_terms}`}
                </p>
                <EvidenceQuote item={b.evidence} />
              </li>
            ))}
          </ul>
        </div>
      )}
      {data.observations && data.observations.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-semibold">Ratings, covenants and observations</h3>
          <ClaimList claims={data.observations} />
        </div>
      )}
    </div>
  )
}
