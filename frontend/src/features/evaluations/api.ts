import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { z } from 'zod'
import { apiGet, apiPost, apiPut, BASE_URL } from '@/lib/api'
import { sourceSchema } from '@/lib/sources'

const statusSchema = z.enum(['draft', 'in_review', 'approved'])
export const findingStatusSchema = z.enum([
  'complete',
  'partial',
  'queued',
  'running',
  'failed',
  'not_run',
])
export type FindingStatus = z.infer<typeof findingStatusSchema>

export const findingSchema = z.object({
  id: z.string(),
  module: z.string(),
  status: findingStatusSchema,
  error: z.string().nullable(),
  summary: z.string(),
  data: z.record(z.string(), z.unknown()),
  evidence: z.array(sourceSchema),
  override_summary: z.string().nullable(),
  override_reason: z.string().nullable(),
})
export type Finding = z.infer<typeof findingSchema>

export const evaluationSummarySchema = z.object({
  id: z.string(),
  company_id: z.string(),
  status: statusSchema,
  formula_version: z.string(),
  created_at: z.string(),
})
export type EvaluationSummary = z.infer<typeof evaluationSummarySchema>

export const evaluationSchema = evaluationSummarySchema.extend({
  prompt_version: z.string(),
  approved_by: z.string().nullable(),
  findings: z.array(findingSchema),
})
export type Evaluation = z.infer<typeof evaluationSchema>

const commentSchema = z.object({
  id: z.string(),
  finding_id: z.string(),
  author: z.string(),
  body: z.string(),
  created_at: z.string(),
})
export type Comment = z.infer<typeof commentSchema>

const auditSchema = z.object({
  id: z.string(),
  entity_type: z.string(),
  entity_id: z.string(),
  action: z.string(),
  actor: z.string(),
  details: z.record(z.string(), z.unknown()),
  created_at: z.string(),
})
export type AuditEvent = z.infer<typeof auditSchema>

const researchQueuedSchema = z.object({ queued: z.boolean(), blockers: z.array(z.string()) })

const isBusy = (e: Evaluation | undefined) =>
  e?.findings.some((f) => f.status === 'queued' || f.status === 'running') ?? false

export function useCompanyEvaluations(companyId: string) {
  return useQuery({
    queryKey: ['companies', companyId, 'evaluations'],
    queryFn: () => apiGet(`/companies/${companyId}/evaluations`, z.array(evaluationSummarySchema)),
  })
}

/** Polls every 3 s while any AI module is queued or running. */
export function useEvaluation(evaluationId: string | undefined) {
  return useQuery({
    queryKey: ['evaluations', evaluationId],
    queryFn: () => apiGet(`/evaluations/${evaluationId}`, evaluationSchema),
    enabled: Boolean(evaluationId),
    refetchInterval: (query) => (isBusy(query.state.data) ? 3000 : false),
  })
}

export function useStartEvaluation(companyId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (actor: string) =>
      apiPost(`/companies/${companyId}/evaluations`, evaluationSchema, {
        actor: actor || 'analyst',
      }),
    onSuccess: (evaluation) => {
      queryClient.setQueryData(['evaluations', evaluation.id], evaluation)
      void queryClient.invalidateQueries({ queryKey: ['companies', companyId, 'evaluations'] })
    },
  })
}

function useEvaluationAction<TBody>(evaluationId: string, path: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: TBody) =>
      apiPost(`/evaluations/${evaluationId}/${path}`, evaluationSchema, body),
    onSuccess: (evaluation) => {
      queryClient.setQueryData(['evaluations', evaluationId], evaluation)
      void queryClient.invalidateQueries({ queryKey: ['evaluations', evaluationId, 'audit'] })
      void queryClient.invalidateQueries({
        queryKey: ['companies', evaluation.company_id, 'evaluations'],
      })
    },
  })
}

export const useSubmitEvaluation = (id: string) =>
  useEvaluationAction<{ actor: string }>(id, 'submit')
export const useApproveEvaluation = (id: string) =>
  useEvaluationAction<{ actor: string }>(id, 'approve')
export const useReturnEvaluation = (id: string) =>
  useEvaluationAction<{ actor: string; reason: string }>(id, 'return')

export function useRunResearch(evaluationId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (actor: string) =>
      apiPost(`/evaluations/${evaluationId}/research`, researchQueuedSchema, { actor }),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ['evaluations', evaluationId] }),
  })
}

export function useAuditTrail(evaluationId: string) {
  return useQuery({
    queryKey: ['evaluations', evaluationId, 'audit'],
    queryFn: () => apiGet(`/evaluations/${evaluationId}/audit`, z.array(auditSchema)),
  })
}

export function useComments(findingId: string) {
  return useQuery({
    queryKey: ['findings', findingId, 'comments'],
    queryFn: () => apiGet(`/findings/${findingId}/comments`, z.array(commentSchema)),
  })
}

export function useAddComment(findingId: string, evaluationId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: { author: string; body: string }) =>
      apiPost(`/findings/${findingId}/comments`, commentSchema, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['findings', findingId, 'comments'] })
      void queryClient.invalidateQueries({ queryKey: ['evaluations', evaluationId, 'audit'] })
    },
  })
}

export function useOverride(findingId: string, evaluationId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: { actor: string; summary: string | null; reason: string | null }) =>
      apiPut(`/findings/${findingId}/override`, findingSchema, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['evaluations', evaluationId] })
    },
  })
}

export function useCapabilities() {
  return useQuery({
    queryKey: ['capabilities'],
    queryFn: () =>
      apiGet('/system/capabilities', z.object({ llm: z.boolean(), embeddings: z.boolean() })),
    staleTime: 5 * 60_000,
  })
}

export const exportUrl = (evaluationId: string, format: 'markdown' | 'json') =>
  `${BASE_URL}/evaluations/${evaluationId}/export?format=${format}`
