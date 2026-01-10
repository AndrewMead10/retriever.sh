import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type {
  LoginData,
  ProjectCreatePayload,
  ProjectCreateResponse,
  ProjectRotateKeyResponse,
  ProjectsOnload,
  RegisterPayload,
  User,
} from '@/lib/types'
import { hasActiveSession } from '@/lib/session'

// Refresh lock to prevent concurrent refresh requests
let refreshPromise: Promise<void> | null = null

// Enhanced fetch with automatic token refresh
async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const response = await fetch(url, options)

  // If we get a 401, try refreshing the token and retry once
  if (response.status === 401 && url !== '/api/auth/refresh') {
    try {
      // If a refresh is already in progress, wait for it
      if (refreshPromise) {
        await refreshPromise
      } else {
        // Start a new refresh
        refreshPromise = fetch('/api/auth/refresh', { method: 'POST' })
          .then(refreshResponse => {
            if (!refreshResponse.ok) {
              throw new Error('Refresh failed')
            }
          })
          .finally(() => {
            refreshPromise = null
          })

        await refreshPromise
      }

      // Retry the original request with the new access token
      return await fetch(url, options)
    } catch (refreshError) {
      // If refresh fails, just throw the error - don't redirect automatically
      throw new Error('Authentication failed')
    }
  }

  return response
}

// API client functions
const apiClient = {
  async login(data: LoginData): Promise<User> {
    const response = await fetch('/api/auth/login/onsubmit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || error.message || 'Login failed')
    }
    const json = await response.json()
    return json.user as User
  },

  async getCurrentUser(): Promise<User> {
    const response = await fetchWithAuth('/api/auth/me')
    if (!response.ok) {
      const err: any = new Error('Not authenticated')
      err.status = response.status
      throw err
    }
    return response.json()
  },

  async register(data: RegisterPayload): Promise<{ success: boolean; message: string }> {
    const response = await fetch('/api/auth/register/onsubmit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || error.message || 'Registration failed')
    }
    return response.json()
  },

  async logout(): Promise<void> {
    await fetchWithAuth('/api/auth/logout/onsubmit', { method: 'POST' })
  },

  async refreshToken(): Promise<void> {
    const response = await fetch('/api/auth/refresh', { method: 'POST' })
    if (!response.ok) {
      throw new Error('Token refresh failed')
    }
  },

  async resetRequest(email: string): Promise<void> {
    const response = await fetch('/api/auth/reset/onsubmit/request', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    })
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || error.message || 'Reset request failed')
    }
  },

  async resetConfirm(token: string, newPassword: string): Promise<void> {
    const response = await fetch('/api/auth/reset/onsubmit/confirm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, new_password: newPassword }),
    })
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || error.message || 'Password reset failed')
    }
  },

  async getPageData(page: string): Promise<any> {
    const response = await fetchWithAuth(`/api/${page}/onload`)
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.detail || error.message || `Failed to load ${page} data`)
    }
    return response.json()
  },

  async getProjects(): Promise<ProjectsOnload> {
    const response = await fetchWithAuth('/api/projects/onload')
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.detail || error.message || 'Failed to load projects')
    }
    return response.json()
  },

  async createProject(payload: ProjectCreatePayload): Promise<ProjectCreateResponse> {
    const response = await fetchWithAuth('/api/projects/onsubmit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.detail || error.message || 'Failed to create project')
    }
    return response.json()
  },

  async deleteProject(projectId: string): Promise<void> {
    const response = await fetchWithAuth('/api/projects/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id: projectId }),
    })
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.detail || error.message || 'Failed to delete project')
    }
  },

  async rotateProjectApiKey(projectId: string): Promise<ProjectRotateKeyResponse> {
    const response = await fetchWithAuth('/api/projects/rotate-api-key', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id: projectId }),
    })
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.detail || error.message || 'Failed to rotate API key')
    }
    return response.json()
  },

  async createCheckout(planSlug: string): Promise<string> {
    const response = await fetchWithAuth(`/api/billing/checkout?plan_slug=${planSlug}`, { method: 'POST' })
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.detail || error.message || 'Failed to create checkout session')
    }
    const data = await response.json()
    return data.url as string
  },

  async openBillingPortal(): Promise<string> {
    const response = await fetchWithAuth('/api/billing/portal', { method: 'POST' })
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.detail || error.message || 'Failed to open billing portal')
    }
    const data = await response.json()
    return data.url as string
  },
}

// Export the api object for use in route loaders
export const api = {
  auth: apiClient,
  getPageData: apiClient.getPageData,
  projects: {
    list: apiClient.getProjects,
    create: apiClient.createProject,
    delete: apiClient.deleteProject,
    rotateKey: apiClient.rotateProjectApiKey,
  },
  billing: {
    checkout: apiClient.createCheckout,
    portal: apiClient.openBillingPortal,
  },
}

// Auth hooks
type UseAuthOptions = {
  fetchUser?: boolean
}

export function useAuth(options: UseAuthOptions = {}) {
  const queryClient = useQueryClient()
  const { fetchUser = true } = options
  const shouldFetchUser = fetchUser && hasActiveSession()

  const login = useMutation({
    mutationFn: apiClient.login,
    onSuccess: (user) => {
      queryClient.setQueryData(['user'], user)
    },
  })

  const register = useMutation({
    mutationFn: apiClient.register,
    onSuccess: (user) => {
      queryClient.setQueryData(['user'], user)
    },
  })

  const logout = useMutation({
    mutationFn: apiClient.logout,
    onSuccess: () => {
      queryClient.setQueryData(['user'], undefined)
      queryClient.clear()
    },
  })

  const refresh = useMutation({
    mutationFn: apiClient.refreshToken,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user'] })
    },
  })

  const userQuery = useQuery({
    queryKey: ['user'],
    queryFn: apiClient.getCurrentUser,
    retry: false,
    enabled: shouldFetchUser,
  })

  return {
    login,
    register,
    logout,
    refresh,
    user: userQuery.data,
    isAuthenticated: !!userQuery.data && !userQuery.isError,
    isLoading: userQuery.isLoading
  }
}

// Page data hook
export function usePageData(page: string) {
  return useQuery({
    queryKey: ['pageData', page],
    queryFn: () => apiClient.getPageData(page),
    retry: (failureCount, error: any) => {
      if (error?.status === 401) return false
      return failureCount < 3
    }
  })
}

type UseProjectsOptions = {
  enabled?: boolean
  refetchOnWindowFocus?: boolean
}

export function useProjects(options: UseProjectsOptions = {}) {
  const { enabled = true, refetchOnWindowFocus = false } = options
  return useQuery({
    queryKey: ['projects'],
    queryFn: apiClient.getProjects,
    refetchOnWindowFocus,
    enabled,
  })
}

export function useCreateProject() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: apiClient.createProject,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
    },
  })
}

export function useDeleteProject() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: apiClient.deleteProject,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
    },
  })
}

export function useRotateProjectKey() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (projectId: string) => apiClient.rotateProjectApiKey(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
    },
  })
}

export function useCreateCheckout() {
  return useMutation({
    mutationFn: (planSlug: string) => apiClient.createCheckout(planSlug),
    onSuccess: (url: string) => {
      // Redirect to Polar checkout
      window.location.href = url
    },
  })
}
