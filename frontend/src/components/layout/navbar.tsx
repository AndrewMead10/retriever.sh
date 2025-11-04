import { Link, useNavigate } from '@tanstack/react-router'
import { useAuth } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { ThemeToggle } from '@/components/layout/theme-toggle'
import { LogOut, User } from 'lucide-react'

export function Navbar() {
  const navigate = useNavigate()
  const { user, logout, isAuthenticated } = useAuth()

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
    <nav className="bg-white shadow-sm border-b">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <Link
              to="/"
              className="text-xl font-semibold text-gray-900 hover:text-gray-700"
            >
              retriever.sh
            </Link>
          </div>

          {isAuthenticated ? (
            <div className="flex items-center space-x-4">
              <Link
                to="/projects"
                className="text-gray-700 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
              >
                Projects
              </Link>
              <Link
                to="/dashboard"
                className="text-gray-700 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
              >
                Dashboard
              </Link>

              <div className="flex items-center space-x-2">
                <ThemeToggle />
                <div className="flex items-center space-x-2 text-sm text-gray-600">
                  <User className="h-4 w-4" />
                  <span>{user?.email}</span>
                </div>

                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleLogout}
                  disabled={logout.isPending}
                >
                  <LogOut className="h-4 w-4" />
                  {logout.isPending ? 'Signing out...' : 'Sign out'}
                </Button>
              </div>
            </div>
          ) : (
            <div className="flex items-center space-x-2">
              <ThemeToggle />
              <Button variant="ghost" size="sm" asChild>
                <Link to="/auth/login" search={{ redirect: undefined }}>Log In</Link>
              </Button>
              <Button variant="default" size="sm" asChild>
                <Link to="/auth/register">Sign Up</Link>
              </Button>
            </div>
          )}
        </div>
      </div>
    </nav>
  )
}
