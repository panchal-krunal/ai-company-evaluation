import { cn } from '@/lib/cn'
import { humanize } from '@/lib/format'
import type { Flag, WhyNotInvestData } from './schemas'

const SEVERITY = {
  high: 'bg-red-50 text-red-800 ring-red-200',
  medium: 'bg-amber-50 text-amber-900 ring-amber-200',
  low: 'bg-slate-100 text-slate-700 ring-slate-200',
} as const

function Reasons({ items }: { items: Flag[] }) {
  return (
    <ul className="space-y-3">
      {items.map((r, i) => (
        <li key={i} className="flex gap-3 text-sm">
          <span
            className={cn(
              'h-fit shrink-0 rounded px-1.5 py-0.5 text-[11px] font-semibold uppercase ring-1',
              SEVERITY[r.severity],
            )}
          >
            {r.severity}
          </span>
          <div>
            <p className="font-medium">{r.title}</p>
            <p className="text-slate-600">{r.explanation}</p>
            <p className="mt-0.5 text-xs text-slate-400">
              From: {r.based_on.map(humanize).join(', ')}
            </p>
          </div>
        </li>
      ))}
    </ul>
  )
}

export function WhyNotInvestView({ data }: { data: WhyNotInvestData }) {
  return (
    <div className="space-y-6">
      {data.ai && (
        <div className="space-y-4">
          <h3 className="text-sm font-semibold">AI case against investing</h3>
          <Reasons items={data.ai.reasons} />
          {data.ai.mitigating_factors.length > 0 && (
            <div>
              <h4 className="mb-1 text-sm font-semibold">Mitigating factors</h4>
              <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
                {data.ai.mitigating_factors.map((m, i) => (
                  <li key={i}>{m}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold">
          Rule-based concerns ({data.rule_based_flags.length})
        </h3>
        {data.rule_based_flags.length ? (
          <Reasons items={data.rule_based_flags} />
        ) : (
          <p className="text-sm text-slate-500">No rule-based concerns.</p>
        )}
      </div>
    </div>
  )
}
