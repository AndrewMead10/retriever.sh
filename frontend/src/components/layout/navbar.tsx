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
  const { data: projectsData } = useProjects({ enabled: isAuthenticated })
  const needsSubscription = isAuthenticated && (projectsData?.needs_subscription || false)

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
              to="/documentation"
              className={`relative text-sm font-mono-jetbrains font-bold px-4 py-2 transition-all duration-200 hover:scale-110 group ${
                isActive('/documentation')
                  ? 'text-foreground font-black'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <span className="relative z-10 transition-colors duration-300 group-hover:text-gray-800">[ DOCS ]</span>
              <div className="absolute inset-x-2 top-1 bottom-1 bg-white opacity-0 group-hover:opacity-100 transition-opacity duration-300 ease-out -z-0 transform origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-300 ease-out"></div>
            </Link>
            {!isAuthenticated || needsSubscription ? (
              <Link
                to="/pricing"
                className={`relative text-sm font-mono-jetbrains font-bold px-4 py-2 transition-all duration-200 hover:scale-110 group ${
                  isActive('/pricing')
                    ? 'text-foreground font-black'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <span className="relative z-10 transition-colors duration-300 group-hover:text-gray-800">[ PRICING ]</span>
                <div className="absolute inset-x-2 top-1 bottom-1 bg-white opacity-0 group-hover:opacity-100 transition-opacity duration-300 ease-out -z-0 transform origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-300 ease-out"></div>
              </Link>
            ) : null}
            <Link
              to="/connect"
              className={`relative text-sm font-mono-jetbrains font-bold px-4 py-2 transition-all duration-200 hover:scale-110 group ${
                isActive('/connect')
                  ? 'text-foreground font-black'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <span className="relative z-10 transition-colors duration-300 group-hover:text-gray-800">[ CONNECT ]</span>
              <div className="absolute inset-x-2 top-1 bottom-1 bg-white opacity-0 group-hover:opacity-100 transition-opacity duration-300 ease-out -z-0 transform origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-300 ease-out"></div>
            </Link>
          </div>

          {isAuthenticated ? (
            <div className="flex items-center space-x-6">
              <div className="hidden md:flex items-center space-x-4">
                <Link
                  to="/projects"
                  className={`relative text-sm font-mono-jetbrains font-bold px-4 py-2 transition-all duration-200 hover:scale-110 group ${
                    isActive('/projects')
                      ? 'text-foreground font-black'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  <span className="relative z-10 transition-colors duration-300 group-hover:text-gray-800">[ PROJECTS ]</span>
                  <div className="absolute inset-x-2 top-1 bottom-1 bg-white opacity-0 group-hover:opacity-100 transition-opacity duration-300 ease-out -z-0 transform origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-300 ease-out"></div>
                </Link>
                <Link
                  to="/billing"
                  search={{ status: undefined }}
                  className={`relative text-sm font-mono-jetbrains font-bold px-4 py-2 transition-all duration-200 hover:scale-110 group ${
                    isActive('/billing')
                      ? 'text-foreground font-black'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  <span className="relative z-10 transition-colors duration-300 group-hover:text-gray-800">[ BILLING ]</span>
                  <div className="absolute inset-x-2 top-1 bottom-1 bg-white opacity-0 group-hover:opacity-100 transition-opacity duration-300 ease-out -z-0 transform origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-300 ease-out"></div>
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
                className="relative text-sm font-mono-jetbrains font-bold text-foreground hover:text-foreground px-4 py-2 sharp-corners border-2 border-foreground bg-card hover:bg-muted transition-all duration-200 overflow-hidden group"
              >
                <span className="relative z-10 transition-colors duration-300 group-hover:text-gray-800">[ LOG IN ]</span>
                <div className="absolute inset-x-2 top-1 bottom-1 bg-white opacity-0 group-hover:opacity-100 transition-opacity duration-300 ease-out -z-0 transform origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-300 ease-out"></div>
              </Link>
              <Link
                to="/auth/register"
                className="relative text-sm font-mono-jetbrains font-bold text-background bg-foreground hover:bg-muted hover:text-foreground px-4 py-2 sharp-corners border-2 border-foreground transition-all duration-200 overflow-hidden group"
              >
                <span className="relative z-10 transition-colors duration-300 group-hover:text-gray-800">[ SIGN UP ]</span>
                <div className="absolute inset-x-2 top-1 bottom-1 bg-white opacity-0 group-hover:opacity-100 transition-opacity duration-300 ease-out -z-0 transform origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-300 ease-out"></div>
              </Link>
              <ThemeToggle />
            </div>
          )}
        </div>
      </div>
    </nav>
  )
}
