import { Link, useNavigate, useRouterState } from '@tanstack/react-router'
import { useAuth, useProjects } from '@/lib/api'
import { ThemeToggle } from '@/components/layout/theme-toggle'
import { LogOut } from 'lucide-react'

export function Navbar() {
  const navigate = useNavigate()
  const location = useRouterState({
    select: (state) => state.location,
  })
  const pathname = location.pathname ?? ''
  const isAuthRoute = pathname.startsWith('/auth')
  const { logout, isAuthenticated } = useAuth({
    fetchUser: !isAuthRoute,
  })
  const { data: projectsData } = useProjects()
  const needsSubscription = projectsData?.needs_subscription || false

  // Helper function to check if a link is active
  const isActive = (path: string) => {
    if (path === '/') {
      return pathname === '/'
    }
    return pathname.startsWith(path)
  }

  const handleLogout = async () => {
    try {
      await logout.mutateAsync()
      navigate({ to: '/auth/login', search: { redirect: undefined } })
    } catch (error) {
      console.error('Logout failed:', error)
      // Still redirect even if logout API call fails
      navigate({ to: '/auth/login', search: { redirect: undefined } })
    }
  }

  return (
    <nav className="bg-background dither-bg border-b-2 border-foreground">
      <div className="mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center space-x-6">
            <Link
              to={isAuthenticated ? "/projects" : "/"}
              className="text-lg font-black font-mono-jetbrains dither-text hover:text-muted-foreground"
            >
              Retriever.sh
            </Link>
          </div>

          <div className="flex items-center space-x-4">
            <Link
              to="/docs"
              className={`text-sm font-mono-jetbrains font-bold px-4 py-2 transition-all duration-200 hover:scale-110 ${
                isActive('/docs')
                  ? 'text-foreground font-black'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              [ DOCS ]
            </Link>
            {!isAuthenticated || needsSubscription ? (
              <Link
                to="/pricing"
                className={`text-sm font-mono-jetbrains font-bold px-4 py-2 transition-all duration-200 hover:scale-110 ${
                  isActive('/pricing')
                    ? 'text-foreground font-black'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                [ PRICING ]
              </Link>
            ) : null}
            <Link
              to="/connect"
              className={`text-sm font-mono-jetbrains font-bold px-4 py-2 transition-all duration-200 hover:scale-110 ${
                isActive('/connect')
                  ? 'text-foreground font-black'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              [ CONNECT ]
            </Link>
          </div>

          {isAuthenticated ? (
            <div className="flex items-center space-x-6">
              <div className="hidden md:flex items-center space-x-4">
                <Link
                  to="/projects"
                  className={`text-sm font-mono-jetbrains font-bold px-4 py-2 transition-all duration-200 hover:scale-110 ${
                    isActive('/projects')
                      ? 'text-foreground font-black'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  [ PROJECTS ]
                </Link>
                <Link
                  to="/billing"
                  search={{ status: undefined }}
                  className={`text-sm font-mono-jetbrains font-bold px-4 py-2 transition-all duration-200 hover:scale-110 ${
                    isActive('/billing')
                      ? 'text-foreground font-black'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  [ BILLING ]
                </Link>
              </div>

              <div className="flex items-center space-x-4">
                <button
                  onClick={handleLogout}
                  disabled={logout.isPending}
                  className="text-sm font-mono-jetbrains font-bold text-foreground bg-card hover:bg-muted border-2 border-foreground px-4 py-2 sharp-corners transition-all duration-200 disabled:opacity-50"
                >
                  <div className="flex items-center space-x-2">
                    <LogOut className="h-3 w-3" />
                    <span>{logout.isPending ? 'EXITING...' : 'LOG OUT'}</span>
                  </div>
                </button>

                <ThemeToggle />
              </div>
            </div>
          ) : (
            <div className="flex items-center space-x-4">
              <Link
                to="/auth/login"
                search={{ redirect: undefined }}
                className="text-sm font-mono-jetbrains font-bold text-foreground hover:text-foreground px-4 py-2 sharp-corners border-2 border-foreground bg-card hover:bg-muted transition-all duration-200"
              >
                [ LOG IN ]
              </Link>
              <Link
                to="/auth/register"
                className="text-sm font-mono-jetbrains font-bold text-background bg-foreground hover:bg-muted hover:text-foreground px-4 py-2 sharp-corners border-2 border-foreground transition-all duration-200"
              >
                [ SIGN UP ]
              </Link>
              <ThemeToggle />
            </div>
          )}
        </div>
      </div>
    </nav>
  )
}
