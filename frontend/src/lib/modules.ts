/** The ten evaluation modules defined in the MVP scope. */
export const EVALUATION_MODULES = [
  { key: 'management_outlook', label: 'Management Outlook' },
  { key: 'products_segments', label: 'Products & Segments' },
  { key: 'industry_outlook', label: 'Industry Outlook' },
  { key: 'competitors', label: 'Competitors' },
  { key: 'debt_structure', label: 'Debt Structure' },
  { key: 'related_party_transactions', label: 'Related Party Transactions' },
  { key: 'financial_warnings', label: 'Financial Warning Checks' },
  { key: 'growth_analysis', label: 'Growth Analysis' },
  { key: 'company_risks', label: 'Company Risks' },
  { key: 'why_not_invest', label: 'Why Not Invest' },
] as const

export type EvaluationModuleKey = (typeof EVALUATION_MODULES)[number]['key']
