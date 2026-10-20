import {
  CircleCheck,
  CircleMinus,
  OctagonAlert,
  TriangleAlert,
  type LucideIcon,
} from 'lucide-react'
import { cn } from '@/lib/cn'

export type WarningStatus = 'clear' | 'watch' | 'flag' | 'not_assessed'

// Status colours are reserved for state and always paired with an icon and a text label.
const STATUS: Record<WarningStatus, { label: string; icon: LucideIcon; className: string }> = {
  clear: {
    label: 'Clear',
    icon: CircleCheck,
    className: 'bg-status-clear/10 [&_svg]:text-status-clear',
  },
  watch: {
    label: 'Watch',
    icon: TriangleAlert,
    className: 'bg-status-watch/15 [&_svg]:text-amber-600',
  },
  flag: {
    label: 'Flag',
    icon: OctagonAlert,
    className: 'bg-status-flag/10 [&_svg]:text-status-flag',
  },
  not_assessed: {
    label: 'Not assessed',
    icon: CircleMinus,
    className: 'bg-slate-100 [&_svg]:text-slate-500',
  },
}

export function WarningStatusBadge({ status }: { status: WarningStatus }) {
  const { label, icon: Icon, className } = STATUS[status]
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap text-slate-800',
        className,
      )}
    >
      <Icon className="size-3.5" aria-hidden />
      {label}
    </span>
  )
}
