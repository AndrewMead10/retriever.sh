import { Link } from '@tanstack/react-router'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

export interface PlanOption {
  slug: string
  label: string
  price: string
  frequency: string
  description: string
  highlight?: boolean
  features: string[]
}

interface PricingCardProps {
  plan: PlanOption
  onSelectPlan?: (slug: string) => void
  selectedPlan?: string | null
  isPending?: boolean
  disabled?: boolean
  actionType?: 'checkout' | 'register' | 'current' | 'select'
  buttonText?: string
  currentPlanSlug?: string
  needsSubscription?: boolean
}

export function PricingCard({
  plan,
  onSelectPlan,
  selectedPlan,
  isPending = false,
  disabled = false,
  actionType = 'checkout',
  buttonText,
  currentPlanSlug,
  needsSubscription = true,
}: PricingCardProps) {
  const isCurrent = currentPlanSlug === plan.slug && !needsSubscription
  const isPlanPending = selectedPlan === plan.slug && isPending

  const getButtonText = () => {
    if (buttonText) return buttonText
    if (isCurrent) return '[ CURRENT PLAN ]'
    if (isPlanPending) return 'REDIRECTING…'

    switch (actionType) {
      case 'register':
        return `[ START ${plan.label} ]`
      case 'checkout':
        return '[ SELECT PLAN ]'
      case 'current':
        return '[ CURRENT PLAN ]'
      case 'select':
        return '[ SELECT PLAN ]'
      default:
        return '[ SELECT PLAN ]'
    }
  }

  const handleClick = () => {
    if (onSelectPlan && !isCurrent && !isPlanPending) {
      onSelectPlan(plan.slug)
    }
  }

  const isButtonDisabled = disabled || isCurrent || isPlanPending

  return (
    <div
      className={`p-8 sharp-corners border-2 ${
        plan.highlight ? 'bg-foreground text-background border-foreground' : 'bg-background border-foreground dither-border'
      }`}
    >
      <div className="text-center">
        <div className="flex items-center justify-between mb-2">
          <div className="text-lg font-bold">{plan.label}</div>
          {plan.highlight && (
            <Badge variant={plan.highlight ? 'secondary' : 'outline'} className="sharp-corners">
              POPULAR
            </Badge>
          )}
        </div>
        <div className="text-4xl font-black mb-4">
          {plan.price}
          <span className="text-lg font-normal">{plan.frequency}</span>
        </div>
        <div className={`text-sm mb-6 ${plan.highlight ? 'text-background/80' : 'text-muted-foreground'}`}>
          {plan.description}
        </div>

        <ul className="text-left space-y-3 mb-8">
          {plan.features.map((feature) => (
            <li key={feature} className="flex items-start space-x-2">
              <span className="font-bold">▶</span>
              <span>{feature}</span>
            </li>
          ))}
        </ul>

        {actionType === 'register' ? (
          <Link
            to="/auth/register"
            className={`block w-full text-center py-3 px-6 sharp-corners font-bold border-2 transition-all duration-200 ${
              plan.highlight
                ? 'bg-background text-foreground border-background hover:bg-muted'
                : 'bg-foreground text-background border-foreground hover:bg-background hover:text-foreground'
            }`}
          >
            {getButtonText()}
          </Link>
        ) : (
          <Button
            disabled={isButtonDisabled}
            onClick={handleClick}
            className={`w-full sharp-corners font-bold border-2 ${
              plan.highlight
                ? 'bg-background text-foreground border-background hover:bg-muted'
                : 'bg-foreground text-background border-foreground hover:bg-background hover:text-foreground'
            } ${isCurrent ? 'opacity-60 cursor-not-allowed' : ''}`}
          >
            {getButtonText()}
          </Button>
        )}
      </div>
    </div>
  )
}

interface PricingSectionProps {
  title?: string
  subtitle?: string
  showHeader?: boolean
  showFooter?: boolean
  plans?: PlanOption[]
  onSelectPlan?: (slug: string) => void
  selectedPlan?: string | null
  isPending?: boolean
  actionType?: 'checkout' | 'register' | 'current' | 'select'
  currentPlanSlug?: string
  needsSubscription?: boolean
  className?: string
}

export function PricingSection({
  title = 'PRICING',
  subtitle = 'Simple, transparent pricing for teams of all sizes. No hidden fees.',
  showHeader = true,
  showFooter = true,
  plans = DEFAULT_PLANS,
  onSelectPlan,
  selectedPlan,
  isPending = false,
  actionType = 'checkout',
  currentPlanSlug,
  needsSubscription = true,
  className = '',
}: PricingSectionProps) {
  return (
    <div className={`${className}`}>
      {showHeader && (
        <div className="text-center mb-12">
          <h2 className="text-4xl font-black dither-text mb-4">{title}</h2>
          <div className="h-1 bg-foreground w-24 mx-auto mb-6"></div>
          <p className="text-muted-foreground max-w-2xl mx-auto">{subtitle}</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {plans.map((plan) => (
          <PricingCard
            key={plan.slug}
            plan={plan}
            onSelectPlan={onSelectPlan}
            selectedPlan={selectedPlan}
            isPending={isPending}
            actionType={actionType}
            currentPlanSlug={currentPlanSlug}
            needsSubscription={needsSubscription}
          />
        ))}
      </div>

      {showFooter && (
        <div className="text-center mt-12">
          <div className="text-sm text-muted-foreground">
            All plans include core features: Authentication, Rate Limiting, Analytics, and API Documentation
          </div>
        </div>
      )}
    </div>
  )
}

export const DEFAULT_PLANS: PlanOption[] = [
  {
    slug: 'tinkering',
    label: 'TINKERING',
    price: '$5',
    frequency: '/mo',
    description: 'Perfect for proving out your stack',
    features: ['5 queries per second', '3 projects', '10k vectors per project'],
  },
  {
    slug: 'building',
    label: 'BUILDING',
    price: '$20',
    frequency: '/mo',
    description: 'For active product development',
    highlight: true,
    features: ['10 queries per second', '20 projects', '100k vectors per project'],
  },
  {
    slug: 'scale',
    label: 'SCALE',
    price: '$50',
    frequency: '/mo',
    description: 'For mission-critical workloads without a sales call',
    features: [
      '100 queries per second',
      'Unlimited projects',
      '250k vectors per project',
      'Advanced access controls',
    ],
  },
]

export default PricingSection
