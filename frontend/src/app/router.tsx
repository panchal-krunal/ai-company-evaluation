import { createBrowserRouter } from 'react-router'
import { AppShell } from '@/components/layout/AppShell'
import { CompaniesPage } from '@/features/companies/CompaniesPage'
import { CompanyPage } from '@/features/companies/CompanyPage'
import { EvaluationPage } from '@/features/evaluations/EvaluationPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <CompaniesPage /> },
      { path: 'companies/:companyId', element: <CompanyPage /> },
      { path: 'evaluations/:evaluationId', element: <EvaluationPage /> },
    ],
  },
])
