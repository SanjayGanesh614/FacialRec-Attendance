// src/store/authStore.ts
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { MeResponse } from '@/types'

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  user: MeResponse | null
  setTokens: (access: string, refresh: string) => void
  setUser: (user: MeResponse) => void
  logout: () => void
  isAdmin: () => boolean
  isSuperAdmin: () => boolean
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,
      user: null,

      setTokens: (access, refresh) =>
        set({ accessToken: access, refreshToken: refresh }),

      setUser: (user) => set({ user }),

      logout: () => {
        set({ accessToken: null, refreshToken: null, user: null })
        window.location.href = '/login'
      },

      isAdmin: () => {
        const role = get().user?.role
        return role === 'super_admin' || role === 'manager'
      },

      isSuperAdmin: () => get().user?.role === 'super_admin',
    }),
    {
      name: 'attendiq-auth',
      // Only persist tokens — refetch user on mount
      partialize: (s) => ({
        accessToken: s.accessToken,
        refreshToken: s.refreshToken,
      }),
    }
  )
)
