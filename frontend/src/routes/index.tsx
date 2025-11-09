import { createFileRoute, Link, redirect } from '@tanstack/react-router'
import { useAuth } from '@/lib/api'
import { queryClient } from '@/routes/__root'
import { api } from '@/lib/api'

export const Route = createFileRoute('/')({
  beforeLoad: async () => {
    try {
      await queryClient.ensureQueryData({
        queryKey: ['user'],
        queryFn: api.auth.getCurrentUser,
      })
      // If we can get the user, they're authenticated, so redirect to projects
      throw redirect({ to: '/projects' })
    } catch {
      // User is not authenticated, continue to home page
    }
  },
  component: HomePage,
})

function HomePage() {
  const { isAuthenticated, user } = useAuth()

  return (
    <div className="min-h-screen bg-background dither-bg font-mono-jetbrains">

      {/* Main content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">

          {/* Left side - Dog image */}
          <div className="flex items-center justify-center">
            <img
              src="/dog_transparent2.png"
              alt="Search API Dog Mascot"
              className="max-w-full h-auto"
            />
          </div>

          {/* Right side - Content and actions */}
          <div className="space-y-8">
            {/* Main title */}
            <div className="space-y-4">
              <h1 className="text-6xl font-black dither-text leading-none">
                RETRIEVER.<span className="font-bold">SH</span>
              </h1>
              <div className="h-1 bg-foreground dither-border"></div>
              <p className="text-lg text-muted-foreground font-mono-jetbrains leading-relaxed">
                Cheap, straightforward search with Claude skill integration.
                No infrastructure setup required - just sign up and start searching.
              </p>
            </div>

            {/* Feature grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="bg-card border border-foreground dither-border sharp-corners p-4">
                <div className="text-xs font-bold mb-2">// CLAUDE SKILL</div>
                <div className="text-sm">Easy AI integration</div>
              </div>
              <div className="bg-card border border-foreground dither-border sharp-corners p-4">
                <div className="text-xs font-bold mb-2">// NO INFRA</div>
                <div className="text-sm">Just sign up & go</div>
              </div>
              <div className="bg-card border border-foreground dither-border sharp-corners p-4">
                <div className="text-xs font-bold mb-2">// CHEAP</div>
                <div className="text-sm">Straightforward pricing</div>
              </div>
              <div className="bg-card border border-foreground dither-border sharp-corners p-4">
                <div className="text-xs font-bold mb-2">// SIMPLE</div>
                <div className="text-sm">Search API</div>
              </div>
            </div>

            {/* Action buttons */}
            <div className="space-y-4 pt-4">
              {isAuthenticated ? (
                <div className="space-y-4">
                  <div className="bg-card border-2 border-foreground dither-border sharp-corners p-4">
                    <div className="text-sm font-bold mb-2"> SESSION ACTIVE</div>
                    <div className="text-sm">Welcome back, {user?.email}</div>
                  </div>
                  <div className="space-y-2">
                    <Link
                      to="/projects"
                      className="block w-full bg-foreground text-background text-center py-4 px-6 sharp-corners border-2 border-foreground font-bold hover:bg-muted hover:text-foreground transition-all duration-200 dither-text"
                    >
                      [ LAUNCH PROJECTS ]
                    </Link>
                  </div>
                </div>
              ) : (
                <div className="space-y-2">
                  <Link
                    to="/auth/login"
                    search={{ redirect: undefined }}
                    className="block w-full bg-foreground text-background text-center py-4 px-6 sharp-corners border-2 border-foreground font-bold hover:bg-muted hover:text-foreground transition-all duration-200 dither-text"
                  >
                    [ SIGN IN ]
                  </Link>
                  <Link
                    to="/auth/register"
                    className="block w-full bg-card text-foreground text-center py-4 px-6 sharp-corners border-2 border-foreground font-bold hover:bg-foreground hover:text-background transition-all duration-200 dither-text"
                  >
                    [ CREATE ACCOUNT ]
                  </Link>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Pricing Section */}
      <div id="pricing" className="mt-16 bg-card border-y border-foreground">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="text-center mb-12">
            <h2 className="text-4xl font-black dither-text mb-4">PRICING</h2>
            <div className="h-1 bg-foreground w-24 mx-auto mb-6"></div>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              Simple, transparent pricing for teams of all sizes. No hidden fees.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Tinkering Plan */}
            <div className="bg-background p-8 border border-foreground dither-border sharp-corners">
              <div className="text-center">
                <div className="text-lg font-bold mb-2">TINKERING</div>
                <div className="text-4xl font-black mb-4">$5<span className="text-lg font-normal">/mo</span></div>
                <div className="text-sm text-muted-foreground mb-6">Perfect for proving out your stack</div>

                <ul className="text-left space-y-3 mb-8">
                  <li className="flex items-start space-x-2">
                    <span className="font-bold">▶</span>
                    <span>1 query per second</span>
                  </li>
                  <li className="flex items-start space-x-2">
                    <span className="font-bold">▶</span>
                    <span>3 projects</span>
                  </li>
                  <li className="flex items-start space-x-2">
                    <span className="font-bold">▶</span>
                    <span>10k vectors per project</span>
                  </li>
                  <li className="flex items-start space-x-2">
                    <span className="font-bold">▶</span>
                    <span>Email support</span>
                  </li>
                </ul>

                <Link
                  to="/auth/register"
                  className="block w-full bg-background border-2 border-foreground text-center py-3 px-6 sharp-corners font-bold hover:bg-foreground hover:text-background transition-all duration-200"
                >
                  [ START TINKERING ]
                </Link>
              </div>
            </div>

            {/* Building Plan */}
            <div className="bg-foreground text-background p-8 relative">
              <div className="absolute -top-3 left-1/2 transform -translate-x-1/2 bg-background px-4 py-1">
                <span className="text-xs font-bold">POPULAR</span>
              </div>
              <div className="text-center">
                <div className="text-lg font-bold mb-2">BUILDING</div>
                <div className="text-4xl font-black mb-4">$20<span className="text-lg font-normal">/mo</span></div>
                <div className="text-sm mb-6">For active product development</div>

                <ul className="text-left space-y-3 mb-8">
                  <li className="flex items-start space-x-2">
                    <span className="font-bold">▶</span>
                    <span>10 queries per second</span>
                  </li>
                  <li className="flex items-start space-x-2">
                    <span className="font-bold">▶</span>
                    <span>20 projects</span>
                  </li>
                  <li className="flex items-start space-x-2">
                    <span className="font-bold">▶</span>
                    <span>100k vectors per project</span>
                  </li>
                  <li className="flex items-start space-x-2">
                    <span className="font-bold">▶</span>
                    <span>Priority support</span>
                  </li>
                </ul>

                <Link
                  to="/auth/register"
                  className="block w-full bg-background text-foreground text-center py-3 px-6 sharp-corners font-bold hover:bg-muted transition-all duration-200"
                >
                  [ START BUILDING ]
                </Link>
              </div>
            </div>

            {/* Scale Plan */}
            <div className="bg-background p-8 border border-foreground dither-border sharp-corners">
              <div className="text-center">
                <div className="text-lg font-bold mb-2">SCALE</div>
                <div className="text-4xl font-black mb-4">$50<span className="text-lg font-normal">/mo</span></div>
                <div className="text-sm text-muted-foreground mb-6">For mission-critical workloads without a sales call</div>

                <ul className="text-left space-y-3 mb-8">
                  <li className="flex items-start space-x-2">
                    <span className="font-bold">▶</span>
                    <span>100 queries per second</span>
                  </li>
                  <li className="flex items-start space-x-2">
                    <span className="font-bold">▶</span>
                    <span>Unlimited projects</span>
                  </li>
                  <li className="flex items-start space-x-2">
                    <span className="font-bold">▶</span>
                    <span>250k vectors per project</span>
                  </li>
                  <li className="flex items-start space-x-2">
                    <span className="font-bold">▶</span>
                    <span>Advanced access controls</span>
                  </li>
                  <li className="flex items-start space-x-2">
                    <span className="font-bold">▶</span>
                    <span>SLA-backed support</span>
                  </li>
                </ul>

                <Link
                  to="/auth/register"
                  className="block w-full bg-background border-2 border-foreground text-center py-3 px-6 sharp-corners font-bold hover:bg-foreground hover:text-background transition-all duration-200"
                >
                  [ START SCALE ]
                </Link>
              </div>
            </div>
          </div>

          <div className="text-center mt-12">
            <div className="text-sm text-muted-foreground">
              All plans include core features: Authentication, Rate Limiting, Analytics, and API Documentation
            </div>
          </div>
        </div>
      </div>

      {/* FAQ Section */}
      <div className="bg-background">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="text-center mb-12">
            <h2 className="text-4xl font-black dither-text mb-4">FREQUENTLY ASKED QUESTIONS</h2>
            <div className="h-1 bg-foreground w-24 mx-auto mb-6"></div>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              Everything you need to know about retriever.sh and our pricing.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-6xl mx-auto">
            {/* FAQ Items */}
            <div className="bg-card p-6 border border-foreground dither-border sharp-corners">
              <div className="flex items-start space-x-3">
                <span className="text-foreground font-bold text-lg">▶</span>
                <div>
                  <h3 className="font-bold mb-2">What makes retriever.sh different?</h3>
                  <p className="text-sm text-muted-foreground">
                    Simple, affordable search with no infrastructure setup and easy Claude skill integration.
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-card p-6 border border-foreground dither-border sharp-corners">
              <div className="flex items-start space-x-3">
                <span className="text-foreground font-bold text-lg">▶</span>
                <div>
                  <h3 className="font-bold mb-2">How does Claude integration work?</h3>
                  <p className="text-sm text-muted-foreground">
                    Our API works seamlessly with Claude's skill system for instant AI-powered search capabilities.
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-card p-6 border border-foreground dither-border sharp-corners">
              <div className="flex items-start space-x-3">
                <span className="text-foreground font-bold text-lg">▶</span>
                <div>
                  <h3 className="font-bold mb-2">How do I get started?</h3>
                  <p className="text-sm text-muted-foreground">
                    Sign up, choose your plan, and get instant API access. No setup required - start searching immediately.
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-card p-6 border border-foreground dither-border sharp-corners">
              <div className="flex items-start space-x-3">
                <span className="text-foreground font-bold text-lg">▶</span>
                <div>
                  <h3 className="font-bold mb-2">Can I change plans anytime?</h3>
                  <p className="text-sm text-muted-foreground">
                    Yes! Upgrade or downgrade anytime. Changes take effect at your next billing cycle.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Terminal-style footer */}
      <div className="border-t-2 border-foreground dither-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <div className="flex items-center space-x-4">
              <span>v1.0.0</span>
              <span>|</span>
              <span className="font-bold">SYSTEM READY</span>
            </div>
            <div className="flex items-center space-x-4">
              <span>© 2024 retriever.sh</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
