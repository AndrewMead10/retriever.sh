import { createFileRoute } from '@tanstack/react-router'
import { useAuth, useCreateCheckout } from '@/lib/api'
import { PricingSection, FAQSection } from '@/components/pricing'

export const Route = createFileRoute('/pricing')({
  component: PricingPage,
})

function PricingPage() {
  const { isAuthenticated } = useAuth()
  const createCheckout = useCreateCheckout()

  const handlePlanSelect = (planSlug: string) => {
    if (isAuthenticated) {
      createCheckout.mutate(planSlug)
    } else {
      // Redirect to register if not authenticated
      window.location.href = '/auth/register'
    }
  }

  return (
    <div className="min-h-screen bg-background dither-bg font-mono-jetbrains">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <PricingSection
          onSelectPlan={handlePlanSelect}
          isPending={createCheckout.isPending}
          actionType="checkout"
        />

        <div className="mt-20">
          <FAQSection />
        </div>
      </div>
    </div>
  )
}
