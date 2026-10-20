import type { ReactNode } from 'react'

/** Loading / error / empty handling for a TanStack Query result. */
export function QueryState<T>({
  query,
  empty,
  children,
}: {
  query: { data: T | undefined; isPending: boolean; error: Error | null }
  empty?: (data: T) => boolean
  children: (data: T) => ReactNode
}) {
  if (query.isPending) return <p className="text-sm text-slate-500">Loading…</p>
  if (query.error)
    return <p className="text-sm text-red-700">Could not load: {query.error.message}</p>
  if (query.data === undefined) return null
  if (empty?.(query.data)) return <p className="text-sm text-slate-500">No data yet.</p>
  return <>{children(query.data)}</>
}
