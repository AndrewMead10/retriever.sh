import { createFileRoute, Link, redirect } from '@tanstack/react-router'
import { useAuth } from '@/lib/api'
import { queryClient } from '@/routes/__root'
import { api } from '@/lib/api'
import { hasActiveSession } from '@/lib/session'
import { PricingSection, FAQSection } from '@/components/pricing'

export const Route = createFileRoute('/')({
  beforeLoad: async () => {
    if (!hasActiveSession()) {
      return
    }
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
                Cheap, easy to use search for your apps. Comes with Claude Code integration out of the box so you can seamlessly add search to your project.
              </p>
            </div>

            {/* Feature grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="bg-card border border-foreground dither-border sharp-corners p-4">
                <div className="text-xs font-bold mb-2">// LOW COST</div>
                <div className="text-sm">Straightforward pricing</div>
              </div>
              <div className="bg-card border border-foreground dither-border sharp-corners p-4">
                <div className="text-xs font-bold mb-2">// SIMPLE</div>
                <div className="text-sm">Add, search, delete; that's all you need.</div>
              </div>
              <div className="bg-card border border-foreground dither-border sharp-corners p-4">
                <div className="text-xs font-bold mb-2">// EASY SETUP</div>
                <div className="text-sm">Just get your API key and go.</div>
              </div>
              <div className="bg-card border border-foreground dither-border sharp-corners p-4">
                <div className="text-xs font-bold mb-2">// CLAUDE SKILL INTEGRATION</div>
                <div className="text-sm">AI ready out of the box.</div>
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
          <PricingSection actionType="register" />
        </div>
      </div>

      {/* FAQ Section */}
      <div className="bg-background">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <FAQSection />
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
