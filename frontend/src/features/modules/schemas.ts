import { z } from 'zod'

/** Shapes of each module's `data`, validated before rendering. */

export const evidenceSchema = z.object({
  passage_id: z.string(),
  quote: z.string(),
  verified: z.boolean(),
  source_document_id: z.string().nullable(),
  document_title: z.string().nullable(),
  page_number: z.number().nullable(),
})
export type EvidenceItem = z.infer<typeof evidenceSchema>

export const claimSchema = z.object({
  statement: z.string(),
  topic: z.string(),
  sentiment: z.enum(['positive', 'negative', 'neutral']),
  supported: z.boolean(),
  evidence: z.array(evidenceSchema),
})
export type ClaimItem = z.infer<typeof claimSchema>

export const researchSchema = z.object({
  claims: z.array(claimSchema),
  open_questions: z.array(z.string()),
  passages_considered: z.number(),
  unsupported_claims: z.number(),
})

export const lineSchema = z.object({
  related_party: z.string(),
  relationship: z.string(),
  nature: z.string(),
  kind: z.enum(['transaction', 'outstanding_balance']),
  year: z.enum(['current', 'previous']),
  amount_as_reported: z.string(),
  unit_as_reported: z.string(),
  amount_cr: z.number().nullable(),
  amount_verified: z.boolean(),
  evidence: evidenceSchema,
})

export const rptSchema = z.object({
  period_label: z.string().nullable(),
  lines: z.array(lineSchema),
  total_transactions_current_cr: z.number().nullable(),
  total_transactions_previous_cr: z.number().nullable(),
  total_balances_current_cr: z.number().nullable(),
  top_parties: z.array(z.object({ related_party: z.string(), amount_cr: z.number() })),
  unverified_lines: z.number(),
  observations: z.array(claimSchema),
})

export const flagSchema = z.object({
  title: z.string(),
  explanation: z.string(),
  severity: z.enum(['high', 'medium', 'low']),
  based_on: z.array(z.string()),
})

export const whyNotInvestSchema = z.object({
  rule_based_flags: z.array(flagSchema),
  ai: z
    .object({
      summary: z.string(),
      reasons: z.array(flagSchema),
      mitigating_factors: z.array(z.string()),
    })
    .nullable(),
})

export const debtYearSchema = z.object({
  period_end: z.string(),
  total_debt: z.number().nullable(),
  net_debt: z.number().nullable(),
  debt_to_equity: z.number().nullable(),
  debt_to_ebitda: z.number().nullable(),
  interest_coverage: z.number().nullable(),
  implied_interest_rate: z.number().nullable(),
  short_term_share: z.number().nullable(),
})

export const borrowingSchema = z.object({
  lender_or_instrument: z.string(),
  facility_type: z.string(),
  secured: z.boolean().nullable(),
  maturity: z.string(),
  amount_as_reported: z.string().nullable(),
  unit_as_reported: z.string(),
  amount_cr: z.number().nullable(),
  amount_verified: z.boolean(),
  interest_rate: z.string().nullable(),
  repayment_terms: z.string().nullable(),
  evidence: evidenceSchema,
})

export const debtSchema = z.object({
  years: z.array(debtYearSchema),
  borrowings: z.array(borrowingSchema).nullable(),
  extracted_total_cr: z.number().nullable().optional(),
  secured_share: z.number().nullable().optional(),
  observations: z.array(claimSchema).optional(),
})

export const metricSchema = z.object({
  key: z.string(),
  label: z.string(),
  higher_is_better: z.boolean(),
  subject: z.number().nullable(),
  peer_median: z.number().nullable(),
  rank: z.number().nullable(),
  better_than_median: z.boolean().nullable(),
})

export const competitorCompanySchema = z.object({
  company_id: z.string(),
  name: z.string(),
  nse_symbol: z.string().nullable(),
  is_subject: z.boolean(),
  period_end: z.string().nullable(),
  values: z.record(z.string(), z.number().nullable()),
})

export const competitorsSchema = z.object({
  metrics: z.array(metricSchema),
  companies: z.array(competitorCompanySchema),
})

export type ResearchData = z.infer<typeof researchSchema>
export type RptData = z.infer<typeof rptSchema>
export type Flag = z.infer<typeof flagSchema>
export type WhyNotInvestData = z.infer<typeof whyNotInvestSchema>
export type DebtData = z.infer<typeof debtSchema>
export type CompetitorsData = z.infer<typeof competitorsSchema>
