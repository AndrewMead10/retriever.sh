import { createFileRoute, redirect } from '@tanstack/react-router'
import { BillingPage, type BillingStatus } from '@/features/billing/billing-page'
import { prefetchBillingData } from '@/features/billing/prefetch'

const allowedStatus: BillingStatus[] = ['success', 'canceled', 'portal', 'error']

export const Route = createFileRoute('/billing/')({
  beforeLoad: async () => {
    try {
      await prefetchBillingData()
    } catch {
      throw redirect({ to: '/auth/login', search: { redirect: '/billing' } })
    }
  },
  validateSearch: (search) => {
    const status = typeof search.status === 'string' && allowedStatus.includes(search.status as BillingStatus)
      ? (search.status as BillingStatus)
      : undefined
    return { status }
  },
  component: BillingRoute,
})

function BillingRoute() {
  const { status } = Route.useSearch()
  return <BillingPage status={status} />
}
