// src/pages/Login.tsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { Fingerprint, Eye, EyeOff } from 'lucide-react'
import toast from 'react-hot-toast'
import { authApi } from '@/api'
import { useAuthStore } from '@/store/authStore'
import { Spinner } from '@/components/ui'

export const LoginPage = () => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPass, setShowPass] = useState(false)
  const { setTokens, setUser } = useAuthStore()
  const navigate = useNavigate()

  const { mutate: login, isPending } = useMutation({
    mutationFn: () => authApi.login(email, password),
    onSuccess: async (data) => {
      setTokens(data.access_token, data.refresh_token)
      const user = await authApi.me()
      setUser(user)
      toast.success(`Welcome back, ${user.full_name.split(' ')[0]}`)
      navigate(user.role === 'employee' ? '/me' : '/admin', { replace: true })
    },
    onError: () => toast.error('Invalid email or password'),
  })

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!email || !password) return
    login()
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative">
      {/* Background texture */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute inset-0"
          style={{
            backgroundImage: 'radial-gradient(circle at 25% 25%, rgba(201,168,76,0.04) 0%, transparent 50%), radial-gradient(circle at 75% 75%, rgba(45,212,160,0.03) 0%, transparent 50%)',
          }}
        />
        {/* Grid */}
        <div className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: 'linear-gradient(var(--border) 1px, transparent 1px), linear-gradient(90deg, var(--border) 1px, transparent 1px)',
            backgroundSize: '48px 48px',
          }}
        />
      </div>

      <div className="relative w-full max-w-sm animate-slide-up">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-[var(--accent)] flex items-center justify-center mx-auto mb-4 shadow-lg shadow-[rgba(201,168,76,0.2)]">
            <Fingerprint size={24} className="text-[#0e0e12]" />
          </div>
          <h1 className="font-display text-2xl font-semibold mb-1">AttendIQ</h1>
          <p className="text-xs text-[var(--muted)] font-mono tracking-widest uppercase">Face Recognition ERP</p>
        </div>

        {/* Form card */}
        <div className="card p-6">
          <p className="text-[11px] font-mono text-[var(--muted)] uppercase tracking-widest mb-5">Sign in to your account</p>

          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="erp-label">Email address</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@company.com"
                className="erp-input"
                autoFocus
                autoComplete="email"
              />
            </div>

            <div>
              <label className="erp-label">Password</label>
              <div className="relative">
                <input
                  type={showPass ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="erp-input pr-10"
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPass(p => !p)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--muted)] hover:text-[var(--text)] transition-colors"
                >
                  {showPass ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isPending || !email || !password}
              className="btn btn-primary w-full justify-center mt-2"
            >
              {isPending ? <Spinner size={14} className="text-[#0e0e12]" /> : null}
              {isPending ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
        </div>

        <p className="text-center text-[10px] text-[var(--dim)] font-mono mt-6">
          ATTENDIQ ERP v1.0 · SECURE ACCESS
        </p>
      </div>
    </div>
  )
}
