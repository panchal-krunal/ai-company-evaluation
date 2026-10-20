import { useQuery } from '@tanstack/react-query'
import { z } from 'zod'
import { apiGet } from '@/lib/api'

export const growthYearSchema = z.object({
  period_end: z.string(),
  revenue: z.number().nullable(),
  revenue_growth: z.number().nullable(),
  gross_margin: z.number().nullable(),
  ebitda_margin: z.number().nullable(),
  net_margin: z.number().nullable(),
})

export const growthSchema = z.object({
  years: z.array(growthYearSchema),
  revenue_cagr_3y: z.number().nullable(),
  revenue_cagr_full: z.number().nullable(),
  full_period_years: z.number(),
  source_document_ids: z.array(z.string()).default([]),
})
export type Growth = z.infer<typeof growthSchema>

export function useCompanyGrowth(companyId: string) {
  return useQuery({
    queryKey: ['companies', companyId, 'growth'],
    queryFn: () => apiGet(`/companies/${companyId}/growth`, growthSchema),
  })
}
