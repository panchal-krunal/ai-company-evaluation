import { Link, useSearchParams } from 'react-router'
import { useCompanies } from './api'

export function CompaniesPage() {
  const [params, setParams] = useSearchParams()
  const includePeers = params.get('peers') === '1'
  const { data, isPending, error } = useCompanies(includePeers)

  return (
    <section>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-semibold">Companies</h1>
        <label className="flex items-center gap-2 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={includePeers}
            onChange={(e) => setParams(e.target.checked ? { peers: '1' } : {})}
          />
          Show peer companies
        </label>
      </div>
      {isPending && <p className="text-slate-500">Loading…</p>}
      {error && <p className="text-red-600">Could not load companies: {error.message}</p>}
      {data && data.length === 0 && (
        <p className="text-slate-500">No companies loaded yet. Run ingestion for the pilot set.</p>
      )}
      {data && data.length > 0 && (
        <table className="w-full overflow-hidden rounded-lg border border-slate-200 bg-white text-sm">
          <thead className="bg-slate-100 text-left">
            <tr>
              <th className="px-3 py-2">Company</th>
              <th className="px-3 py-2">NSE</th>
              <th className="px-3 py-2">BSE</th>
              <th className="px-3 py-2">Sector</th>
            </tr>
          </thead>
          <tbody>
            {data.map((c) => (
              <tr key={c.id} className="border-t border-slate-100 hover:bg-slate-50">
                <td className="px-3 py-2">
                  <Link className="text-indigo-700 hover:underline" to={`/companies/${c.id}`}>
                    {c.name}
                  </Link>
                  {c.coverage === 'peer' && (
                    <span className="ml-2 rounded bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-600">
                      Peer
                    </span>
                  )}
                </td>
                <td className="px-3 py-2">{c.nse_symbol ?? '—'}</td>
                <td className="px-3 py-2">{c.bse_code ?? '—'}</td>
                <td className="px-3 py-2">{c.sector ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
