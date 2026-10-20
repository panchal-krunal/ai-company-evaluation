import { ArrowLeft, Play } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { QueryState } from '@/components/ui/QueryState'
import { Section } from '@/components/ui/Section'
import { cn } from '@/lib/cn'
import { fiscalYear, formatDateTime } from '@/lib/format'
import { sourceMap } from '@/lib/sources'
import { useCompanyEvaluations, useStartEvaluation } from '../evaluations/api'
import { EvaluationStatusBadge } from '../evaluations/EvaluationStatusBadge'
import { FinancialStatements } from '../financials/FinancialStatements'
import { useCompanyGrowth } from '../growth/api'
import { GrowthView } from '../growth/GrowthView'
import { useCompanyWarnings } from '../warnings/api'
import { WarningsTable, WarningSummary } from '../warnings/WarningsTable'
import { useAnalystName } from '@/lib/analyst'
import { useCompany, useCompanyPeers, useCompanySources } from './api'
import { DocumentsList } from './DocumentsList'

const TABS = [
  { key: 'overview', label: 'Overview' },
  { key: 'financials', label: 'Financial statements' },
  { key: 'documents', label: 'Documents' },
  { key: 'evaluations', label: 'Evaluations' },
] as const
type Tab = (typeof TABS)[number]['key']

export function CompanyPage() {
  const { companyId = '' } = useParams()
  const navigate = useNavigate()
  const [tab, setTab] = useState<Tab>('overview')
  const company = useCompany(companyId)
  const sources = sourceMap(useCompanySources(companyId).data)
  const warnings = useCompanyWarnings(companyId)
  const growth = useCompanyGrowth(companyId)
  const evaluations = useCompanyEvaluations(companyId)
  const startEvaluation = useStartEvaluation(companyId)
  const peers = useCompanyPeers(companyId)
  const analyst = useAnalystName()

  const start = () =>
    startEvaluation.mutate(analyst, {
      onSuccess: (evaluation) => void navigate(`/evaluations/${evaluation.id}`),
    })

  return (
    <div className="space-y-6">
      <Link
        to="/"
        className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800"
      >
        <ArrowLeft className="size-4" aria-hidden /> Companies
      </Link>

      <QueryState query={company}>
        {(c) => (
          <header className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h1 className="text-2xl font-semibold">{c.name}</h1>
              <p className="mt-1 flex flex-wrap gap-x-4 text-sm text-slate-500">
                {c.nse_symbol && <span>NSE: {c.nse_symbol}</span>}
                {c.bse_code && <span>BSE: {c.bse_code}</span>}
                {c.isin && <span>ISIN: {c.isin}</span>}
                {c.sector && <span>{c.sector}</span>}
              </p>
              {peers.data && peers.data.length > 0 && (
                <p className="mt-1 text-sm text-slate-500">
                  Peers:{' '}
                  {peers.data.map((p, i) => (
                    <span key={p.id}>
                      {i > 0 && ', '}
                      <Link to={`/companies/${p.id}`} className="text-indigo-700 hover:underline">
                        {p.name}
                      </Link>
                    </span>
                  ))}
                </p>
              )}
            </div>
            <div className="flex flex-col items-end gap-1">
              <button
                type="button"
                onClick={start}
                disabled={startEvaluation.isPending}
                className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
              >
                <Play className="size-4" aria-hidden />
                {startEvaluation.isPending ? 'Running…' : 'Start evaluation'}
              </button>
              {startEvaluation.error && (
                <p className="text-xs text-red-700">{startEvaluation.error.message}</p>
              )}
            </div>
          </header>
        )}
      </QueryState>

      <nav
        role="tablist"
        aria-label="Company sections"
        className="flex gap-1 border-b border-slate-200"
      >
        {TABS.map((t) => (
          <button
            key={t.key}
            role="tab"
            type="button"
            aria-selected={tab === t.key}
            onClick={() => setTab(t.key)}
            className={cn(
              '-mb-px border-b-2 px-3 py-2 text-sm',
              tab === t.key
                ? 'border-indigo-600 font-medium text-indigo-700'
                : 'border-transparent text-slate-600 hover:text-slate-900',
            )}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab === 'overview' && (
        <div className="space-y-6">
          <Section
            title="Financial warning checks"
            description={
              warnings.data?.as_of
                ? `${fiscalYear(warnings.data.as_of)} · consolidated · formula v${warnings.data.formula_version} (placeholder thresholds)`
                : undefined
            }
            actions={warnings.data && <WarningSummary results={warnings.data.results} />}
          >
            <QueryState query={warnings}>
              {(report) => <WarningsTable results={report.results} sources={sources} />}
            </QueryState>
          </Section>
          <Section title="Growth analysis" description="Consolidated, annual">
            <QueryState query={growth} empty={(g) => g.years.length === 0}>
              {(g) => <GrowthView growth={g} />}
            </QueryState>
          </Section>
        </div>
      )}

      {tab === 'financials' && (
        <Section
          title="Financial statements"
          description="Every figure links to the source it was taken from"
        >
          <FinancialStatements companyId={companyId} sources={sources} />
        </Section>
      )}

      {tab === 'documents' && (
        <Section
          title="Documents"
          description="Filings ingested for AI research; open any document to read the source"
        >
          <DocumentsList companyId={companyId} />
        </Section>
      )}

      {tab === 'evaluations' && (
        <Section title="Evaluations">
          <QueryState query={evaluations} empty={(list) => list.length === 0}>
            {(list) => (
              <ul className="divide-y divide-slate-100">
                {list.map((e) => (
                  <li
                    key={e.id}
                    className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm"
                  >
                    <Link
                      to={`/evaluations/${e.id}`}
                      className="font-medium text-indigo-700 hover:underline"
                    >
                      Evaluation of {formatDateTime(e.created_at)}
                    </Link>
                    <span className="flex items-center gap-3 text-slate-500">
                      formula v{e.formula_version}
                      <EvaluationStatusBadge status={e.status} />
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </QueryState>
        </Section>
      )}
    </div>
  )
}
