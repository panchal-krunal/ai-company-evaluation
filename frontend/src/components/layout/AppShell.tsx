import { BarChart3, UserRound } from 'lucide-react'
import { Link, Outlet } from 'react-router'
import { setAnalystName, useAnalystName } from '@/lib/analyst'

export function AppShell() {
  const analyst = useAnalystName()
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3">
          <Link to="/" className="flex items-center gap-2 font-semibold">
            <BarChart3 className="size-5 text-indigo-600" aria-hidden />
            Company Evaluation Platform
          </Link>
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <UserRound className="size-4" aria-hidden />
            <span className="sr-only">Analyst name</span>
            <input
              value={analyst}
              onChange={(e) => setAnalystName(e.target.value)}
              placeholder="Your name"
              className="w-40 rounded-md border border-slate-300 px-2 py-1 text-sm focus:border-indigo-500 focus:outline-none"
            />
          </label>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
