import { ExternalLink, FileText } from 'lucide-react'
import { QueryState } from '@/components/ui/QueryState'
import { SourceBadge } from '@/components/ui/SourceLinks'
import { documentUrl } from '@/lib/api'
import { cn } from '@/lib/cn'
import { formatDateTime, humanize } from '@/lib/format'
import { useCompanyDocuments } from './api'

const STATUS: Record<string, string> = {
  embedded: 'bg-emerald-50 text-emerald-800',
  extracted: 'bg-amber-50 text-amber-900',
  registered: 'bg-slate-100 text-slate-700',
  failed: 'bg-red-50 text-red-800',
}

const STATUS_HELP: Record<string, string> = {
  embedded: 'Searchable by the AI research modules',
  extracted: 'Text extracted; embeddings pending (needs VOYAGE_API_KEY)',
  registered: 'Stored; text not extracted yet',
  failed: 'Ingestion failed',
}

export function DocumentsList({ companyId }: { companyId: string }) {
  const docs = useCompanyDocuments(companyId)
  return (
    <QueryState query={docs} empty={(d) => d.length === 0}>
      {(list) => (
        <ul className="divide-y divide-slate-100">
          {list.map((d) => (
            <li
              key={d.id}
              className="flex flex-wrap items-start justify-between gap-3 py-3 text-sm"
            >
              <div className="space-y-1">
                <a
                  href={documentUrl(d.id)}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 font-medium text-indigo-700 hover:underline"
                >
                  <FileText className="size-4" aria-hidden />
                  {d.title}
                </a>
                <p className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                  {d.doc_type && <span>{humanize(d.doc_type)}</span>}
                  {d.page_count != null && <span>· {d.page_count} pages</span>}
                  {d.filing_date && (
                    <span>· filed {formatDateTime(d.filing_date).split(',')[0]}</span>
                  )}
                  <span>
                    · {d.embedded_chunks}/{d.chunks} passages embedded
                  </span>
                  <SourceBadge isPrimary={d.is_primary} />
                  {d.source_url && (
                    <a
                      href={d.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-0.5 hover:underline"
                    >
                      {d.publisher} <ExternalLink className="size-3" aria-hidden />
                    </a>
                  )}
                </p>
                {d.ingestion_error && <p className="text-xs text-red-700">{d.ingestion_error}</p>}
              </div>
              <span
                title={STATUS_HELP[d.ingestion_status]}
                className={cn(
                  'rounded-full px-2 py-0.5 text-xs font-medium',
                  STATUS[d.ingestion_status],
                )}
              >
                {humanize(d.ingestion_status)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </QueryState>
  )
}
