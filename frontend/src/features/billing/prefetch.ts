import { api } from '@/lib/api'
import { hasActiveSession } from '@/lib/session'
import { queryClient } from '@/routes/__root'

export async function prefetchBillingData() {
  if (!hasActiveSession()) {
    throw new Error('unauthenticated')
  }
  await queryClient.ensureQueryData({
    queryKey: ['user'],
    queryFn: api.auth.getCurrentUser,
  })
  await queryClient.ensureQueryData({
    queryKey: ['projects'],
    queryFn: api.projects.list,
  })
}
