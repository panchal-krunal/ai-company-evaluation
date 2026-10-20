import { CircleAlert, FileText } from 'lucide-react'
import { documentUrl } from '@/lib/api'
import type { ClaimItem, EvidenceItem } from './schemas'

/** A quoted passage, linked to the source PDF at the cited page. Unverified quotes are flagged. */
export function EvidenceQuote({ item }: { item: EvidenceItem }) {
  return (
    <blockquote className="border-l-2 border-slate-200 pl-3 text-xs text-slate-600">
      <p className="italic">“{item.quote}”</p>
      {item.verified && item.source_document_id ? (
        <a
          href={documentUrl(item.source_document_id, item.page_number)}
          target="_blank"
          rel="noreferrer"
          className="mt-0.5 inline-flex items-center gap-1 text-indigo-700 hover:underline"
        >
          <FileText className="size-3" aria-hidden />
          {item.document_title}
          {item.page_number ? `, p.${item.page_number}` : ''}
        </a>
      ) : (
        <span className="mt-0.5 inline-flex items-center gap-1 font-medium text-red-700">
          <CircleAlert className="size-3" aria-hidden />
          Quote not found in the cited passage
        </span>
      )}
    </blockquote>
  )
}

const SENTIMENT = {
  positive: 'bg-emerald-50 text-emerald-800',
  negative: 'bg-red-50 text-red-800',
  neutral: 'bg-slate-100 text-slate-700',
} as const

export function ClaimList({ claims }: { claims: ClaimItem[] }) {
  if (claims.length === 0) return <p className="text-sm text-slate-500">No claims.</p>
  return (
    <ul className="space-y-4">
      {claims.map((c, i) => (
        <li key={i} className="space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium tracking-wide text-slate-500 uppercase">
              {c.topic}
            </span>
            <span className={`rounded px-1.5 py-0.5 text-[11px] ${SENTIMENT[c.sentiment]}`}>
              {c.sentiment}
            </span>
            {!c.supported && (
              <span className="rounded bg-red-100 px-1.5 py-0.5 text-[11px] font-medium text-red-800">
                Unsupported — do not rely on this
              </span>
            )}
          </div>
          <p
            className={
              c.supported ? 'text-sm' : 'text-sm text-slate-500 line-through decoration-slate-300'
            }
          >
            {c.statement}
          </p>
          <div className="space-y-1.5">
            {c.evidence.map((e, j) => (
              <EvidenceQuote key={j} item={e} />
            ))}
          </div>
        </li>
      ))}
    </ul>
  )
}
