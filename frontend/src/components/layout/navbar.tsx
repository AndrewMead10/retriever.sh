import { Link, useNavigate, useRouterState } from '@tanstack/react-router'
import { useAuth } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { ThemeToggle } from '@/components/layout/theme-toggle'
import { LogOut, User } from 'lucide-react'

export function Navbar() {
  const navigate = useNavigate()
  const location = useRouterState({
    select: (state) => state.location,
  })
  const pathname = location.pathname ?? ''
  const isAuthRoute = pathname.startsWith('/auth')
  const { user, logout, isAuthenticated } = useAuth({
    fetchUser: !isAuthRoute,
  })

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
              to="/"
              className="text-lg font-black font-mono-jetbrains dither-text hover:text-muted-foreground"
            >
              Retriever.sh
            </Link>
          </div>

          <div className="flex items-center space-x-4">
            <Link
              to="/docs"
              className="text-sm font-mono-jetbrains font-bold text-muted-foreground hover:text-foreground px-4 py-2 transition-all duration-200 hover:scale-110"
            >
              [ DOCS ]
            </Link>
            <Link
              to="/"
              hash="pricing"
              className="text-sm font-mono-jetbrains font-bold text-muted-foreground hover:text-foreground px-4 py-2 transition-all duration-200 hover:scale-110"
            >
              [ PRICING ]
            </Link>
            <Link
              to="/connect"
              className="text-sm font-mono-jetbrains font-bold text-muted-foreground hover:text-foreground px-4 py-2 transition-all duration-200 hover:scale-110"
            >
              [ CONNECT ]
            </Link>
          </div>

          {isAuthenticated ? (
            <div className="flex items-center space-x-6">
              <div className="hidden md:flex items-center space-x-4">
                <Link
                  to="/projects"
                  className="text-sm font-mono-jetbrains font-bold text-muted-foreground hover:text-foreground px-4 py-2 sharp-corners border border-transparent hover:border-foreground transition-all duration-200"
                >
                  [ PROJECTS ]
                </Link>
              </div>

              <div className="flex items-center space-x-4">
                <div className="bg-card border border-foreground dither-border sharp-corners px-3 py-2">
                  <div className="flex items-center space-x-2 text-sm font-mono-jetbrains">
                    <User className="h-3 w-3" />
                    <span className="truncate max-w-32">{user?.email}</span>
                  </div>
                </div>

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
