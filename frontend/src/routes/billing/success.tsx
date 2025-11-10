import { createFileRoute, redirect } from '@tanstack/react-router'
import { BillingPage } from '@/features/billing/billing-page'
import { prefetchBillingData } from '@/features/billing/prefetch'

export const Route = createFileRoute('/billing/success')({
  beforeLoad: async () => {
    try {
      await prefetchBillingData()
    } catch {
      throw redirect({ to: '/auth/login', search: { redirect: '/billing/success' } })
    }
  },
  component: () => <BillingPage status="success" />,
})
