import { useEffect, useMemo, useState } from 'react'
import { Link } from '@tanstack/react-router'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'
import { PricingSection, type PlanOption } from '@/components/pricing'
import { api, useCreateCheckout, useProjects } from '@/lib/api'
import { formatNumber } from '@/utils/format'

export type BillingStatus = 'success' | 'canceled' | 'portal' | 'error'

const STATUS_BANNERS: Record<BillingStatus, { title: string; body: string; tone: 'success' | 'warning' | 'info' | 'destructive' }> = {
  success: {
    title: 'Checkout complete',
    body: 'Your subscription is active. Usage and limits have refreshed below.',
    tone: 'success',
  },
  canceled: {
    title: 'Checkout canceled',
    body: 'No changes were made. You can restart the upgrade flow at any time.',
    tone: 'warning',
  },
  portal: {
    title: 'Billing portal closed',
    body: 'Billing updates have been saved. Give us a moment to sync your subscription.',
    tone: 'info',
  },
  error: {
    title: 'Billing error',
    body: 'Something went wrong while processing your billing action. Please try again or contact support.',
    tone: 'destructive',
  },
}

const BILLING_PLANS: PlanOption[] = [
  {
    slug: 'tinkering',
    label: 'TINKERING',
    price: '$5',
    frequency: '/mo',
    description: 'Perfect for proving out your RAG stack.',
    features: ['5 queries per second', '3 projects', '≈10k vectors per project'],
  },
  {
    slug: 'building',
    label: 'BUILDING',
    price: '$20',
    frequency: '/mo',
    description: 'For actively building and shipping features.',
    highlight: true,
    features: ['10 queries per second', '20 projects', '≈100k vectors per project'],
  },
  {
    slug: 'scale',
    label: 'SCALE',
    price: '$50',
    frequency: '/mo',
    description: 'High QPS and per-project capacity for production workloads.',
    features: ['100 queries per second', 'Unlimited projects', '250k vectors per project'],
  },
]

export function BillingPage({ status }: { status?: BillingStatus }) {
  const queryClient = useQueryClient()
  const { data, isLoading, error } = useProjects()
  const createCheckout = useCreateCheckout()
  const [pendingSlug, setPendingSlug] = useState<string | null>(null)
  const portal = useMutation({
    mutationFn: api.billing.portal,
    onSuccess: (url) => {
      window.location.href = url
    },
    onError: (err: any) => {
      toast.error(err?.message || 'Unable to open billing portal')
    },
  })

  useEffect(() => {
    queryClient.invalidateQueries({ queryKey: ['projects'] })
  }, [queryClient])

  const statusBanner = status ? STATUS_BANNERS[status] : undefined
  const needsSubscription = data?.needs_subscription ?? true
  const plan = data?.plan
  const usage = data?.usage

  const vectorLimit = plan?.vector_limit ?? usage?.vector_limit ?? null
  const projectLimit = usage?.project_limit ?? null

  const projectPercent = useMemo(() => {
    if (!usage || !projectLimit || projectLimit <= 0) {
      return 0
    }
    return Math.min(100, Math.round((usage.project_count / projectLimit) * 100))
  }, [usage, projectLimit])

  const planDisplayPrice = plan ? `$${plan.price_cents / 100}/mo` : '$0/mo'

  const handlePlanSelect = (slug: string) => {
    if (!needsSubscription && plan?.slug === slug) {
      return
    }
    setPendingSlug(slug)
    createCheckout.mutate(slug, {
      onError: (err: any) => {
        toast.error(err?.message || 'Unable to start checkout')
        setPendingSlug(null)
      },
    })
  }

  const planHeader = needsSubscription
    ? 'Choose a plan to unlock projects and vector storage.'
    : `${plan?.name ?? 'Your'} subscription is active.`

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background dither-bg font-mono-jetbrains">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          Loading billing data...
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background dither-bg font-mono-jetbrains">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-16 space-y-4">
          <div className="text-2xl font-black">BILLING</div>
          <div className="text-red-500">Failed to load billing information: {String((error as any)?.message || 'Unknown error')}</div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background dither-bg font-mono-jetbrains">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-16 space-y-8">
        <div className="space-y-3">
          <p className="text-xs text-muted-foreground tracking-wide">// CONTROL PANEL</p>
          <h1 className="text-4xl font-black dither-text">BILLING</h1>
          <p className="text-muted-foreground max-w-3xl">Manage your subscription, usage, and Polar checkout flows.</p>
        </div>

        {statusBanner && (
          <div
            className={`border-2 sharp-corners px-5 py-4 font-mono-jetbrains ${
              statusBanner.tone === 'success'
                ? 'border-green-500 bg-green-500/10 text-green-600 dark:text-green-400'
                : statusBanner.tone === 'warning'
                  ? 'border-yellow-500 bg-yellow-500/10 text-yellow-600 dark:text-yellow-400'
                  : statusBanner.tone === 'info'
                    ? 'border-blue-500 bg-blue-500/10 text-blue-600 dark:text-blue-400'
                    : 'border-red-500 bg-red-500/10 text-red-600 dark:text-red-400'
            }`}
          >
            <p className="text-sm font-bold uppercase">{statusBanner.title}</p>
            <p className="text-xs mt-1">{statusBanner.body}</p>
          </div>
        )}

        <Card className="bg-card border-2 border-foreground dither-border sharp-corners">
          <CardHeader className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <CardTitle className="text-xl font-black dither-text">{plan?.name?.toUpperCase() || 'NO PLAN'}</CardTitle>
              <CardDescription className="font-mono-jetbrains text-sm">{planHeader}</CardDescription>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="ghost"
                asChild
                className="bg-card border border-foreground dither-border sharp-corners font-bold hover:bg-muted transition-all duration-200"
              >
                <Link to="/projects">[ BACK TO PROJECTS ]</Link>
              </Button>
              <Button
                variant="ghost"
                asChild
                className="bg-card border border-foreground dither-border sharp-corners font-bold hover:bg-muted transition-all duration-200"
              >
                <Link to="/pricing">[ VIEW PRICING ]</Link>
              </Button>
              {!needsSubscription && (
                <Button
                  onClick={() => portal.mutate()}
                  disabled={portal.isPending}
                  className="bg-foreground text-background border-2 border-foreground sharp-corners font-bold hover:bg-muted hover:text-foreground transition-all duration-200"
                >
                  {portal.isPending ? 'OPENING PORTAL...' : '[ BILLING PORTAL ]'}
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-3">
            <SummaryItem label="PRICE" value={needsSubscription ? '--' : planDisplayPrice} />
            <SummaryItem label="QUERY QPS" value={plan ? `${plan.query_qps_limit}` : '--'} help="per second" />
            <SummaryItem label="PROJECTS" value={formatLimit(projectLimit, needsSubscription)} />
          </CardContent>
        </Card>

        <section>
          <PricingSection
            title={undefined}
            subtitle={undefined}
            showHeader={false}
            showFooter={false}
            plans={BILLING_PLANS}
            onSelectPlan={handlePlanSelect}
            selectedPlan={pendingSlug}
            isPending={createCheckout.isPending}
            actionType="checkout"
            currentPlanSlug={plan?.slug}
            needsSubscription={needsSubscription}
          />
        </section>

        {needsSubscription ? (
          <Card className="bg-card border-2 border-red-500 sharp-corners">
            <CardHeader>
              <CardTitle className="text-xl font-black text-red-600 dark:text-red-400">START A SUBSCRIPTION</CardTitle>
              <CardDescription className="font-mono-jetbrains text-sm">
                Pick a plan above to enable project creation, ingestion, and hybrid search.
              </CardDescription>
            </CardHeader>
          </Card>
        ) : (
          plan && usage && (
            <Card className="bg-card border-2 border-foreground dither-border sharp-corners">
              <CardHeader>
                <CardTitle className="text-xl font-black dither-text">USAGE</CardTitle>
                <CardDescription className="font-mono-jetbrains text-sm">
                  Current month totals update live as you ingest and query.
                </CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-2">
                <UsagePanel
                  title="Vectors"
                  primary={vectorLimit && vectorLimit > 0 ? `${formatNumber(vectorLimit)} per project` : 'Unlimited per project'}
                  help={`${formatNumber(usage.total_vectors)} stored across all projects`}
                />
                <UsagePanel
                  title="Projects"
                  primary={`${formatNumber(usage.project_count)} / ${formatLimit(projectLimit, needsSubscription)}`}
                  help="Active projects"
                  percent={projectPercent}
                />
                <UsagePanel title="Queries" primary={formatNumber(usage.total_queries)} help="Total hybrid queries" />
                <UsagePanel title="Ingest requests" primary={formatNumber(usage.total_ingest_requests)} help="Documents processed" />
              </CardContent>
            </Card>
          )
        )}
      </div>
    </div>
  )
}

function SummaryItem({ label, value, help }: { label: string; value: string; help?: string }) {
  return (
    <div className="space-y-1">
      <p className="text-xs text-muted-foreground">// {label}</p>
      <p className="text-2xl font-black dither-text">{value}</p>
      {help && <p className="text-xs text-muted-foreground">{help}</p>}
    </div>
  )
}

function UsagePanel({ title, primary, help, percent }: { title: string; primary: string; help?: string; percent?: number }) {
  return (
    <div className="bg-background border border-foreground dither-border sharp-corners p-4 space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-foreground">// {title.toUpperCase()}</p>
        {typeof percent === 'number' && percent > 0 && (
          <Badge variant="outline" className="sharp-corners">
            {percent}%
          </Badge>
        )}
      </div>
      <p className="text-3xl font-black dither-text">{primary}</p>
      {help && <p className="text-xs text-muted-foreground">{help}</p>}
      {typeof percent === 'number' && percent > 0 && (
        <>
          <Progress value={percent} className="h-2 mt-2" />
          <Separator className="border-dashed" />
        </>
      )}
    </div>
  )
}

function formatLimit(limit: number | null | undefined, needsSubscription?: boolean) {
  if (limit === null || limit === undefined) {
    return needsSubscription ? '0' : 'Unlimited'
  }
  if (limit < 0) {
    return 'Unlimited'
  }
  return formatNumber(limit)
}
