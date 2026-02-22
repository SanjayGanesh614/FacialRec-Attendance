// src/api/client.ts
// Central axios instance — handles auth headers and token refresh automatically.

import axios from 'axios'
import { useAuthStore } from '@/store/authStore'

const client = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 10_000,
})

// ── Request interceptor — attach access token ─────────────────────────────────
client.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ── Response interceptor — handle 401 / token refresh ────────────────────────
let refreshing = false
let queue: Array<{ resolve: (v: string) => void; reject: (e: unknown) => void }> = []

client.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    if (error.response?.status !== 401 || original._retry) {
      return Promise.reject(error)
    }
    original._retry = true

    if (refreshing) {
      // Queue requests that come in while we're already refreshing
      return new Promise((resolve, reject) => {
        queue.push({ resolve, reject })
      }).then((token) => {
        original.headers.Authorization = `Bearer ${token}`
        return client(original)
      })
    }

    refreshing = true
    const refreshToken = useAuthStore.getState().refreshToken

    try {
      const { data } = await axios.post('/api/v1/auth/refresh', {
        refresh_token: refreshToken,
      })
      const newToken: string = data.access_token
      useAuthStore.getState().setTokens(newToken, refreshToken!)
      queue.forEach((p) => p.resolve(newToken))
      queue = []
      original.headers.Authorization = `Bearer ${newToken}`
      return client(original)
    } catch (e) {
      queue.forEach((p) => p.reject(e))
      queue = []
      useAuthStore.getState().logout()
      return Promise.reject(e)
    } finally {
      refreshing = false
    }
  }
)

export default client
