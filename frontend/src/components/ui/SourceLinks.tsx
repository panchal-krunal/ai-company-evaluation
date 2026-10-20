import { ExternalLink } from 'lucide-react'
import type { Source } from '@/lib/sources'

export function SourceBadge({ isPrimary }: { isPrimary: boolean }) {
  return isPrimary ? (
    <span className="rounded bg-emerald-50 px-1.5 py-0.5 text-[11px] font-medium text-emerald-800">
      Primary
    </span>
  ) : (
    <span
      className="rounded bg-amber-50 px-1.5 py-0.5 text-[11px] font-medium text-amber-900"
      title="Aggregator page compiled from filings. Reconcile with the annual report before relying on it."
    >
      Secondary
    </span>
  )
}

export function SourceLinks({ ids, sources }: { ids: string[]; sources: Map<string, Source> }) {
  if (ids.length === 0) return null
  return (
    <ul className="flex flex-wrap gap-x-3 gap-y-1 text-xs">
      {ids.map((id) => {
        const source = sources.get(id)
        if (!source)
          return (
            <li key={id} className="text-slate-400">
              Unknown source
            </li>
          )
        const label = source.publisher ?? source.title
        return (
          <li key={id} className="inline-flex items-center gap-1">
            {source.url ? (
              <a
                href={source.url}
                target="_blank"
                rel="noreferrer"
                title={source.title}
                className="inline-flex items-center gap-0.5 text-indigo-700 hover:underline"
              >
                {label}
                <ExternalLink className="size-3" aria-hidden />
              </a>
            ) : (
              <span title={source.title}>{label}</span>
            )}
            <SourceBadge isPrimary={source.isPrimary} />
          </li>
        )
      })}
    </ul>
  )
}

export function EvidenceList({ sources }: { sources: Source[] }) {
  if (sources.length === 0) return <p className="text-sm text-slate-500">No sources recorded.</p>
  return (
    <ul className="divide-y divide-slate-100 text-sm">
      {sources.map((s) => (
        <li key={s.id} className="flex flex-wrap items-center gap-2 py-2">
          {s.url ? (
            <a
              href={s.url}
              target="_blank"
              rel="noreferrer"
              className="text-indigo-700 hover:underline"
            >
              {s.title}
            </a>
          ) : (
            <span>{s.title}</span>
          )}
          {s.publisher && <span className="text-slate-500">· {s.publisher}</span>}
          <SourceBadge isPrimary={s.isPrimary} />
        </li>
      ))}
    </ul>
  )
}
