import { useMemo, useState } from 'react'
import { QueryState } from '@/components/ui/QueryState'
import { SourceLinks } from '@/components/ui/SourceLinks'
import { cn } from '@/lib/cn'
import { fiscalYear, formatByUnit, humanize, quarterLabel, UNIT_LABELS } from '@/lib/format'
import type { Source } from '@/lib/sources'
import { useFinancials } from '../companies/api'
import { METRIC_LABELS, pivotFacts } from './pivot'

export function FinancialStatements({
  companyId,
  sources,
}: {
  companyId: string
  sources: Map<string, Source>
}) {
  const [periodType, setPeriodType] = useState<'FY' | 'Q'>('FY')
  const query = useFinancials(companyId, periodType)
  const table = useMemo(() => (query.data ? pivotFacts(query.data) : undefined), [query.data])
  const label = periodType === 'FY' ? fiscalYear : quarterLabel

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div
          role="tablist"
          aria-label="Period"
          className="inline-flex rounded-md border border-slate-200 p-0.5"
        >
          {(['FY', 'Q'] as const).map((p) => (
            <button
              key={p}
              role="tab"
              type="button"
              aria-selected={periodType === p}
              onClick={() => setPeriodType(p)}
              className={cn(
                'rounded px-3 py-1 text-sm',
                periodType === p ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100',
              )}
            >
              {p === 'FY' ? 'Annual' : 'Quarterly'}
            </button>
          ))}
        </div>
        <p className="text-xs text-slate-500">Consolidated · ₹ Cr unless stated</p>
      </div>

      <QueryState query={{ ...query, data: table }} empty={(t) => t.sections.length === 0}>
        {({ periods, sections }) => (
          <div className="overflow-x-auto">
            <table className="w-full text-sm tabular-nums">
              <thead className="text-xs tracking-wide text-slate-500 uppercase">
                <tr className="border-b border-slate-200">
                  <th className="sticky left-0 bg-white py-2 pr-4 text-left font-medium">Metric</th>
                  {periods.map((p) => (
                    <th key={p} className="py-2 pr-4 text-right font-medium whitespace-nowrap">
                      {label(p)}
                    </th>
                  ))}
                  <th className="py-2 text-left font-medium">Source</th>
                </tr>
              </thead>
              {sections.map((section) => (
                <tbody key={section.title}>
                  <tr>
                    <th
                      colSpan={periods.length + 2}
                      className="bg-slate-50 px-2 py-1.5 text-left text-xs font-semibold text-slate-700"
                    >
                      {section.title}
                    </th>
                  </tr>
                  {section.rows.map((row) => (
                    <tr key={row.metric} className="border-b border-slate-100">
                      <td className="sticky left-0 bg-white py-1.5 pr-4 whitespace-nowrap">
                        {METRIC_LABELS[row.metric] ?? humanize(row.metric)}
                        {row.unit !== 'INR_CR' && (
                          <span className="ml-1 text-xs text-slate-400">
                            ({UNIT_LABELS[row.unit] ?? row.unit})
                          </span>
                        )}
                      </td>
                      {periods.map((p) => {
                        const value = row.values.get(p)
                        return (
                          <td
                            key={p}
                            className={cn(
                              'py-1.5 pr-4 text-right whitespace-nowrap',
                              value != null && value < 0 && 'text-red-700',
                            )}
                          >
                            {formatByUnit(value, row.unit)}
                          </td>
                        )
                      })}
                      <td className="py-1.5">
                        <SourceLinks ids={row.sourceIds} sources={sources} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              ))}
            </table>
          </div>
        )}
      </QueryState>
    </div>
  )
}
