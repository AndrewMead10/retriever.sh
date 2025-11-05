import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import { useForm } from 'react-hook-form'
import { useAuth } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import type { RegisterData } from '@/lib/types'

function GoogleIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 24 24">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
    </svg>
  )
}

export const Route = createFileRoute('/auth/register/')({
  component: RegisterPage,
})

function RegisterPage() {
  const navigate = useNavigate()
  const { register: registerUser } = useAuth({ fetchUser: false })
  const { register, handleSubmit, watch, formState: { errors } } = useForm<RegisterData>()
  
  const password = watch('password')

  const onSubmit = async (data: RegisterData) => {
    try {
      await registerUser.mutateAsync({
        email: data.email,
        password: data.password
      })
      navigate({ to: '/dashboard' })
    } catch (error) {
      console.error('Registration failed:', error)
    }
  }

  const handleGoogleSignIn = () => {
    window.location.href = '/auth/google/login'
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Create Account</CardTitle>
          <CardDescription>
            Sign up to get started with your account
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <Input
                type="email"
                placeholder="Email"
                {...register('email', { 
                  required: 'Email is required',
                  pattern: {
                    value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                    message: 'Invalid email address'
                  }
                })}
              />
              {errors.email && (
                <p className="text-sm text-destructive mt-1">{errors.email.message}</p>
              )}
            </div>
            
            <div>
              <Input
                type="password"
                placeholder="Password"
                {...register('password', { 
                  required: 'Password is required',
                  minLength: {
                    value: 8,
                    message: 'Password must be at least 8 characters'
                  }
                })}
              />
              {errors.password && (
                <p className="text-sm text-destructive mt-1">{errors.password.message}</p>
              )}
            </div>
            
            <div>
              <Input
                type="password"
                placeholder="Confirm Password"
                {...register('confirmPassword', {
                  required: 'Please confirm your password',
                  validate: value => value === password || 'Passwords do not match'
                })}
              />
              {errors.confirmPassword && (
                <p className="text-sm text-destructive mt-1">{errors.confirmPassword.message}</p>
              )}
            </div>
            
            {registerUser.isError && (
              <p className="text-sm text-destructive">
                {String((registerUser.error as any)?.message || 'Registration failed')}
              </p>
            )}

            {registerUser.isSuccess && (
              <p className="text-sm text-green-600 dark:text-green-400">
                Account created successfully! Redirecting...
              </p>
            )}
            
            <Button 
              type="submit" 
              className="w-full"
              disabled={registerUser.isPending}
            >
              {registerUser.isPending ? 'Creating account...' : 'Create Account'}
            </Button>
          </form>

          <div className="mt-6">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t border-border" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-background px-2 text-muted-foreground">
                  Or continue with
                </span>
              </div>
            </div>
            <Button
              type="button"
              variant="outline"
              className="mt-4 w-full"
              onClick={handleGoogleSignIn}
            >
              <GoogleIcon />
              Continue with Google
            </Button>
          </div>

          <div className="mt-4 text-center">
            <Link
              to="/auth/login"
              search={{ redirect: undefined }}
              className="text-sm text-primary hover:text-primary/80"
            >
              Already have an account? Sign in
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
