import { createFileRoute, Link } from '@tanstack/react-router'
import { useAuth } from '@/lib/api'

export const Route = createFileRoute('/')({
  component: HomePage,
})

function HomePage() {
  const { isAuthenticated, user } = useAuth()

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            retriever.sh
          </h1>
          <p className="text-gray-600 mb-8">
            Configure retrieval projects, manage limits, and plug RAG into your product.
          </p>
          
          {isAuthenticated ? (
            <div className="space-y-4">
              <p className="text-green-600">
                Welcome back, {user?.email}!
              </p>
              <div className="space-y-2">
                <Link
                  to="/projects"
                  className="block w-full bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 transition-colors"
                >
                  Go to Projects
                </Link>
                {/* Admin Panel link removed */}
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <Link
                to="/auth/login"
                search={{ redirect: undefined }}
                className="block w-full bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 transition-colors"
              >
                Sign In
              </Link>
              <Link
                to="/auth/register"
                className="block w-full bg-gray-600 text-white py-2 px-4 rounded hover:bg-gray-700 transition-colors"
              >
                Sign Up
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
