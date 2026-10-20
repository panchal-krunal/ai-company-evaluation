import {
  CircleAlert,
  CircleCheck,
  CircleDashed,
  CircleDot,
  CircleDotDashed,
  Loader,
  type LucideIcon,
} from 'lucide-react'
import { cn } from '@/lib/cn'
import type { FindingStatus } from '../evaluations/api'

const STATUS: Record<FindingStatus, { label: string; icon: LucideIcon; className: string }> = {
  complete: { label: 'Complete', icon: CircleCheck, className: 'text-emerald-700' },
  partial: { label: 'Partial', icon: CircleDotDashed, className: 'text-amber-700' },
  queued: { label: 'Queued', icon: CircleDot, className: 'text-indigo-600' },
  running: { label: 'Running', icon: Loader, className: 'text-indigo-600 [&_svg]:animate-spin' },
  failed: { label: 'Failed', icon: CircleAlert, className: 'text-red-700' },
  not_run: { label: 'Not run', icon: CircleDashed, className: 'text-slate-500' },
}

export function FindingStatusBadge({
  status,
  compact = false,
}: {
  status: FindingStatus
  compact?: boolean
}) {
  const { label, icon: Icon, className } = STATUS[status]
  return (
    <span
      className={cn('inline-flex items-center gap-1 text-xs font-medium', className)}
      title={label}
    >
      <Icon className="size-3.5" aria-hidden />
      {compact ? <span className="sr-only">{label}</span> : label}
    </span>
  )
}
