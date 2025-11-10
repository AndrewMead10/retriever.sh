import { createFileRoute, redirect } from '@tanstack/react-router'
import { BillingPage } from '@/features/billing/billing-page'
import { prefetchBillingData } from '@/features/billing/prefetch'

export const Route = createFileRoute('/billing/portal')({
  beforeLoad: async () => {
    try {
      await prefetchBillingData()
    } catch {
      throw redirect({ to: '/auth/login', search: { redirect: '/billing/portal' } })
    }
  },
  component: () => <BillingPage status="portal" />,
})
