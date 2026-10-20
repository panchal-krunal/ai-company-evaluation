import { useQuery } from '@tanstack/react-query'
import { z } from 'zod'
import { apiGet } from '@/lib/api'

export const warningStatusSchema = z.enum(['clear', 'watch', 'flag', 'not_assessed'])

export const warningResultSchema = z.object({
  check: z.string(),
  status: warningStatusSchema,
  value: z.number().nullable(),
  explanation: z.string(),
  inputs: z.record(z.string(), z.number().nullable()),
  source_document_ids: z.array(z.string()).default([]),
})
export type WarningResult = z.infer<typeof warningResultSchema>

export const warningReportSchema = z.object({
  formula_version: z.string(),
  as_of: z.string().nullable(),
  results: z.array(warningResultSchema),
})

export function useCompanyWarnings(companyId: string) {
  return useQuery({
    queryKey: ['companies', companyId, 'warnings'],
    queryFn: () => apiGet(`/companies/${companyId}/warnings`, warningReportSchema),
  })
}
