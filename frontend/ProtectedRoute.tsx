// src/components/shared/ProtectedRoute.tsx
import { Navigate, Outlet } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '@/store/authStore'
import { authApi } from '@/api'
import { PageLoader } from '@/components/ui'

interface Props {
  requireAdmin?: boolean
  requireSuperAdmin?: boolean
}

export const ProtectedRoute = ({ requireAdmin, requireSuperAdmin }: Props) => {
  const { accessToken, setUser, user } = useAuthStore()

  // If no token at all, redirect to login
  if (!accessToken) return <Navigate to="/login" replace />

  // Load current user if not in store yet
  const { isLoading, isError } = useQuery({
    queryKey: ['me'],
    queryFn: async () => {
      const u = await authApi.me()
      setUser(u)
      return u
    },
    enabled: !user,
    retry: false,
  })

  if (isLoading) return <PageLoader />

  // Token invalid / expired
  if (isError) {
    useAuthStore.getState().logout()
    return <Navigate to="/login" replace />
  }

  if (!user) return <PageLoader />

  // Role checks
  if (requireSuperAdmin && user.role !== 'super_admin') {
    return <Navigate to="/admin" replace />
  }

  if (requireAdmin && user.role === 'employee') {
    return <Navigate to="/me" replace />
  }

  return <Outlet />
}
