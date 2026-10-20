import { ArrowLeft, Download, RotateCcw, Send, ShieldCheck, Sparkles } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { z } from 'zod'
import { QueryState } from '@/components/ui/QueryState'
import { Section } from '@/components/ui/Section'
import { EvidenceList } from '@/components/ui/SourceLinks'
import { useAnalystName } from '@/lib/analyst'
import { cn } from '@/lib/cn'
import { fiscalYear, formatDateTime } from '@/lib/format'
import { EVALUATION_MODULES, type EvaluationModuleKey } from '@/lib/modules'
import { sourceMap } from '@/lib/sources'
import { useCompany } from '../companies/api'
import { growthSchema } from '../growth/api'
import { GrowthView } from '../growth/GrowthView'
import { CommentsPanel, OverridePanel } from '../modules/AnalystPanel'
import { CompetitorsView } from '../modules/CompetitorsView'
import { DebtView } from '../modules/DebtView'
import { FindingStatusBadge } from '../modules/FindingStatusBadge'
import {
  competitorsSchema,
  debtSchema,
  researchSchema,
  rptSchema,
  whyNotInvestSchema,
} from '../modules/schemas'
import { ResearchView } from '../modules/ResearchView'
import { RptView } from '../modules/RptView'
import { WhyNotInvestView } from '../modules/WhyNotInvestView'
import { warningResultSchema } from '../warnings/api'
import { WarningsTable, WarningSummary } from '../warnings/WarningsTable'
import {
  exportUrl,
  useApproveEvaluation,
  useEvaluation,
  useReturnEvaluation,
  useRunResearch,
  useSubmitEvaluation,
  type Evaluation,
  type Finding,
} from './api'
import { AuditTrail } from './AuditTrail'
import { EvaluationStatusBadge } from './EvaluationStatusBadge'

const warningsDataSchema = z.object({ as_of: z.string(), results: z.array(warningResultSchema) })
const RESEARCH_MODULES = [
  'management_outlook',
  'products_segments',
  'industry_outlook',
  'company_risks',
]

function FindingBody({ finding }: { finding: Finding }) {
  const sources = sourceMap(finding.evidence)
  const parse = <T,>(schema: z.ZodType<T>) => schema.safeParse(finding.data)

  if (finding.module === 'financial_warnings') {
    const p = parse(warningsDataSchema)
    if (p.success)
      return (
        <div className="space-y-3">
          <WarningSummary results={p.data.results} />
          <WarningsTable results={p.data.results} sources={sources} />
        </div>
      )
  }
  if (finding.module === 'growth_analysis') {
    const p = parse(growthSchema)
    if (p.success) return <GrowthView growth={p.data} />
  }
  if (finding.module === 'competitors') {
    const p = parse(competitorsSchema)
    if (p.success) return <CompetitorsView data={p.data} />
  }
  if (finding.module === 'debt_structure') {
    const p = parse(debtSchema)
    if (p.success) return <DebtView data={p.data} />
  }
  if (finding.module === 'related_party_transactions') {
    const p = parse(rptSchema)
    if (p.success) return <RptView data={p.data} />
  }
  if (RESEARCH_MODULES.includes(finding.module)) {
    const p = parse(researchSchema)
    if (p.success) return <ResearchView data={p.data} />
  }
  if (finding.module === 'why_not_invest') {
    const p = parse(whyNotInvestSchema)
    if (p.success) return <WhyNotInvestView data={p.data} />
  }
  return (
    <pre className="overflow-x-auto rounded bg-slate-50 p-3 text-xs">
      {JSON.stringify(finding.data, null, 2)}
    </pre>
  )
}

const btn =
  'inline-flex items-center gap-1.5 rounded-md px-3 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50'

function ActionBar({ evaluation }: { evaluation: Evaluation }) {
  const analyst = useAnalystName()
  const research = useRunResearch(evaluation.id)
  const submit = useSubmitEvaluation(evaluation.id)
  const approve = useApproveEvaluation(evaluation.id)
  const back = useReturnEvaluation(evaluation.id)
  const busy = evaluation.findings.some((f) => f.status === 'queued' || f.status === 'running')
  const error = research.error ?? submit.error ?? approve.error ?? back.error
  const blockers = research.data && !research.data.queued ? research.data.blockers : []

  return (
    <div className="flex flex-col items-end gap-2">
      <div className="flex flex-wrap justify-end gap-2">
        {evaluation.status !== 'approved' && (
          <button
            type="button"
            disabled={!analyst || busy || research.isPending}
            onClick={() => research.mutate(analyst)}
            className={cn(btn, 'border border-slate-300 bg-white hover:bg-slate-50')}
          >
            <Sparkles className="size-4" aria-hidden />{' '}
            {busy ? 'AI research running…' : 'Run AI research'}
          </button>
        )}
        {evaluation.status === 'draft' && (
          <button
            type="button"
            disabled={!analyst || submit.isPending}
            onClick={() => submit.mutate({ actor: analyst })}
            className={cn(btn, 'bg-indigo-600 text-white hover:bg-indigo-700')}
          >
            <Send className="size-4" aria-hidden /> Submit for review
          </button>
        )}
        {evaluation.status === 'in_review' && (
          <>
            <button
              type="button"
              disabled={!analyst || back.isPending}
              onClick={() => {
                const reason = window.prompt('Why is this going back to draft?')
                if (reason) back.mutate({ actor: analyst, reason })
              }}
              className={cn(btn, 'border border-slate-300 bg-white hover:bg-slate-50')}
            >
              <RotateCcw className="size-4" aria-hidden /> Return to draft
            </button>
            <button
              type="button"
              disabled={!analyst || busy || approve.isPending}
              onClick={() => approve.mutate({ actor: analyst })}
              className={cn(btn, 'bg-emerald-700 text-white hover:bg-emerald-800')}
            >
              <ShieldCheck className="size-4" aria-hidden /> Approve
            </button>
          </>
        )}
        <a
          href={exportUrl(evaluation.id, 'markdown')}
          className={cn(btn, 'border border-slate-300 bg-white hover:bg-slate-50')}
        >
          <Download className="size-4" aria-hidden /> Export
        </a>
        <a
          href={exportUrl(evaluation.id, 'json')}
          className={cn(btn, 'text-slate-600 hover:bg-slate-100')}
        >
          JSON
        </a>
      </div>
      {!analyst && (
        <p className="text-xs text-amber-800">Enter your name at the top of the page to act.</p>
      )}
      {error && <p className="text-sm text-red-700">{error.message}</p>}
      {blockers.length > 0 && (
        <p className="max-w-md text-right text-sm text-amber-900">
          AI research can’t run yet: {blockers.join('; ')}.
        </p>
      )}
    </div>
  )
}

export function EvaluationPage() {
  const { evaluationId } = useParams()
  const evaluation = useEvaluation(evaluationId)
  const company = useCompany(evaluation.data?.company_id)
  const [active, setActive] = useState<EvaluationModuleKey>('financial_warnings')

  return (
    <QueryState query={evaluation}>
      {(ev) => {
        const findings = new Map(ev.findings.map((f) => [f.module, f]))
        const module = EVALUATION_MODULES.find((m) => m.key === active)
        const finding = findings.get(active)
        const asOf = (finding?.data as { as_of?: string } | undefined)?.as_of
        const locked = ev.status === 'approved'
        const done = ev.findings.filter((f) => f.status === 'complete').length

        return (
          <div className="space-y-6">
            <Link
              to={`/companies/${ev.company_id}`}
              className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800"
            >
              <ArrowLeft className="size-4" aria-hidden /> {company.data?.name ?? 'Company'}
            </Link>

            <header className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-3">
                  <h1 className="text-2xl font-semibold">
                    Evaluation · {company.data?.name ?? '…'}
                  </h1>
                  <EvaluationStatusBadge status={ev.status} />
                </div>
                <p className="mt-1 text-sm text-slate-500">
                  Created {formatDateTime(ev.created_at)} · formula v{ev.formula_version} · prompts
                  v{ev.prompt_version}
                  {ev.approved_by && ` · approved by ${ev.approved_by}`} · {done} of{' '}
                  {EVALUATION_MODULES.length} modules complete
                </p>
              </div>
              <ActionBar evaluation={ev} />
            </header>

            <div className="grid gap-6 md:grid-cols-[250px_1fr]">
              <nav aria-label="Evaluation modules" className="flex flex-col gap-1">
                {EVALUATION_MODULES.map((m) => {
                  const f = findings.get(m.key)
                  return (
                    <button
                      key={m.key}
                      type="button"
                      onClick={() => setActive(m.key)}
                      aria-current={m.key === active ? 'page' : undefined}
                      className={cn(
                        'flex items-center justify-between gap-2 rounded-md px-3 py-2 text-left text-sm',
                        m.key === active
                          ? 'bg-indigo-600 text-white [&_span]:text-white'
                          : 'hover:bg-slate-200',
                      )}
                    >
                      {m.label}
                      {f && <FindingStatusBadge status={f.status} compact />}
                    </button>
                  )
                })}
              </nav>

              <div className="min-w-0 space-y-6">
                <Section
                  title={module?.label ?? active}
                  description={asOf ? `${fiscalYear(asOf)} · consolidated` : 'Consolidated'}
                  actions={finding && <FindingStatusBadge status={finding.status} />}
                >
                  {!finding ? (
                    <p className="text-sm text-slate-500">
                      This module is not part of this evaluation.
                    </p>
                  ) : (
                    <div className="space-y-5">
                      {finding.error && (
                        <p
                          className={cn(
                            'rounded-md p-3 text-sm',
                            finding.status === 'failed'
                              ? 'bg-red-50 text-red-800'
                              : 'bg-amber-50 text-amber-900',
                          )}
                        >
                          {finding.error}
                        </p>
                      )}
                      {finding.summary && (
                        <p className="rounded-md bg-slate-50 p-3 text-sm">{finding.summary}</p>
                      )}
                      {['complete', 'partial'].includes(finding.status) && (
                        <FindingBody finding={finding} />
                      )}
                      {['queued', 'running'].includes(finding.status) && (
                        <p className="text-sm text-slate-500">
                          This module is {finding.status}; the page updates automatically.
                        </p>
                      )}
                    </div>
                  )}
                </Section>

                {finding && !['not_run', 'queued', 'running'].includes(finding.status) && (
                  <>
                    <Section
                      title="Analyst review"
                      description="Override the conclusion (with a reason) and discuss it"
                    >
                      <div className="grid gap-6 lg:grid-cols-2">
                        <OverridePanel
                          key={finding.id}
                          finding={finding}
                          evaluationId={ev.id}
                          locked={locked}
                        />
                        <CommentsPanel findingId={finding.id} evaluationId={ev.id} />
                      </div>
                    </Section>
                    {finding.evidence.length > 0 && (
                      <Section
                        title="Sources"
                        description="Documents the figures and quotes in this module come from"
                      >
                        <EvidenceList sources={finding.evidence} />
                      </Section>
                    )}
                  </>
                )}

                <Section title="Audit trail" description="Every action on this evaluation">
                  <AuditTrail evaluationId={ev.id} />
                </Section>
              </div>
            </div>
          </div>
        )
      }}
    </QueryState>
  )
}
