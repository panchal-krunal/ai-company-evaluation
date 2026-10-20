import { useQuery } from '@tanstack/react-query'
import { z } from 'zod'
import { apiGet } from '@/lib/api'
import { sourceSchema } from '@/lib/sources'

export const companySchema = z.object({
  id: z.string(),
  name: z.string(),
  nse_symbol: z.string().nullable(),
  bse_code: z.string().nullable(),
  isin: z.string().nullable().optional(),
  sector: z.string().nullable(),
  coverage: z.enum(['evaluated', 'peer']).default('evaluated'),
})
export type Company = z.infer<typeof companySchema>

export const financialFactSchema = z.object({
  metric: z.string(),
  period_end: z.string(),
  period_type: z.enum(['FY', 'Q']),
  basis: z.enum(['consolidated', 'standalone']),
  value: z.number(),
  unit: z.string(),
  source_document_id: z.string().nullable(),
})
export type FinancialFact = z.infer<typeof financialFactSchema>

export function useCompanies(includePeers = false) {
  return useQuery({
    queryKey: ['companies', { includePeers }],
    queryFn: () => apiGet(`/companies?include_peers=${includePeers}`, z.array(companySchema)),
  })
}

export function useCompany(companyId: string | undefined) {
  return useQuery({
    queryKey: ['companies', companyId],
    queryFn: () => apiGet(`/companies/${companyId}`, companySchema),
    enabled: Boolean(companyId),
  })
}

export function useFinancials(companyId: string, periodType: 'FY' | 'Q') {
  return useQuery({
    queryKey: ['companies', companyId, 'financials', periodType],
    queryFn: () =>
      apiGet(
        `/companies/${companyId}/financials?period_type=${periodType}`,
        z.array(financialFactSchema),
      ),
  })
}

export function useCompanySources(companyId: string) {
  return useQuery({
    queryKey: ['companies', companyId, 'sources'],
    queryFn: () => apiGet(`/companies/${companyId}/sources`, z.array(sourceSchema)),
  })
}

export const documentSchema = z.object({
  id: z.string(),
  title: z.string(),
  doc_type: z.string().nullable(),
  source_url: z.string().nullable(),
  publisher: z.string().nullable(),
  is_primary: z.boolean(),
  page_count: z.number().nullable(),
  ingestion_status: z.string(),
  ingestion_error: z.string().nullable(),
  period_end: z.string().nullable(),
  filing_date: z.string().nullable(),
  chunks: z.number(),
  embedded_chunks: z.number(),
})
export type SourceDocumentRow = z.infer<typeof documentSchema>

export function useCompanyDocuments(companyId: string) {
  return useQuery({
    queryKey: ['companies', companyId, 'documents'],
    queryFn: () => apiGet(`/companies/${companyId}/documents`, z.array(documentSchema)),
  })
}

export function useCompanyPeers(companyId: string) {
  return useQuery({
    queryKey: ['companies', companyId, 'peers'],
    queryFn: () => apiGet(`/companies/${companyId}/peers`, z.array(companySchema)),
  })
}
