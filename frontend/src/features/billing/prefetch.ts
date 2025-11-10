import { api } from '@/lib/api'
import { queryClient } from '@/routes/__root'

export async function prefetchBillingData() {
  await queryClient.ensureQueryData({
    queryKey: ['user'],
    queryFn: api.auth.getCurrentUser,
  })
  await queryClient.ensureQueryData({
    queryKey: ['projects'],
    queryFn: api.projects.list,
  })
}
