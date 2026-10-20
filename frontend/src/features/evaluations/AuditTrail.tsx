import { formatDateTime, humanize } from '@/lib/format'
import { useAuditTrail } from './api'

export function AuditTrail({ evaluationId }: { evaluationId: string }) {
  const audit = useAuditTrail(evaluationId)
  if (!audit.data) return <p className="text-sm text-slate-500">Loading…</p>
  return (
    <ol className="space-y-2 text-sm">
      {audit.data.map((e) => {
        const module = typeof e.details.module === 'string' ? e.details.module : null
        const reason = typeof e.details.reason === 'string' ? e.details.reason : null
        return (
          <li key={e.id} className="flex flex-wrap gap-x-2">
            <span className="text-slate-500 tabular-nums">{formatDateTime(e.created_at)}</span>
            <span className="font-medium">{e.actor}</span>
            <span>{humanize(e.action).toLowerCase()}</span>
            {module && <span className="text-slate-500">· {humanize(module)}</span>}
            {reason && <span className="text-slate-500">· “{reason}”</span>}
          </li>
        )
      })}
    </ol>
  )
}
