import { cn } from '@/lib/cn'
import type { EvaluationSummary } from './api'

const STYLES: Record<EvaluationSummary['status'], string> = {
  draft: 'bg-slate-100 text-slate-700',
  in_review: 'bg-indigo-50 text-indigo-800',
  approved: 'bg-emerald-50 text-emerald-800',
}

export function EvaluationStatusBadge({ status }: { status: EvaluationSummary['status'] }) {
  return (
    <span className={cn('rounded-full px-2 py-0.5 text-xs font-medium capitalize', STYLES[status])}>
      {status.replace('_', ' ')}
    </span>
  )
}
