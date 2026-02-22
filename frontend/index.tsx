// src/components/ui/index.tsx
// Shared primitive UI components used throughout the app.

import { type ReactNode } from 'react'
import { cn, getInitials } from '@/utils'
import { Loader2, X } from 'lucide-react'

// ── Stat Card ─────────────────────────────────────────────────────────────────
interface StatCardProps {
  label: string
  value: string | number
  sub?: string
  accent?: 'amber' | 'green' | 'red' | 'sky'
  icon?: ReactNode
}
export const StatCard = ({ label, value, sub, accent = 'amber', icon }: StatCardProps) => (
  <div className={cn('card p-5 animate-fade-in', `card-accent-${accent === 'amber' ? 'amber' : accent === 'green' ? 'green' : accent === 'red' ? 'red' : 'sky'}`)}>
    <div className="flex items-start justify-between">
      <div>
        <p className="text-[11px] font-mono uppercase tracking-widest text-[var(--muted)] mb-2">{label}</p>
        <p className="font-display text-3xl font-semibold tracking-tight">{value}</p>
        {sub && <p className="text-xs text-[var(--muted)] mt-1.5">{sub}</p>}
      </div>
      {icon && <div className="text-[var(--muted)] opacity-60">{icon}</div>}
    </div>
  </div>
)

// ── Avatar ────────────────────────────────────────────────────────────────────
interface AvatarProps { name: string; size?: 'sm' | 'md' | 'lg' }
export const Avatar = ({ name, size = 'md' }: AvatarProps) => {
  const sizes = { sm: 'w-7 h-7 text-[10px]', md: 'w-9 h-9 text-xs', lg: 'w-12 h-12 text-sm' }
  return (
    <div className={cn(
      'rounded-full flex items-center justify-center font-mono font-semibold flex-shrink-0',
      'bg-[var(--bg-4)] border border-[var(--border-l)] text-[var(--accent)]',
      sizes[size]
    )}>
      {getInitials(name)}
    </div>
  )
}

// ── Spinner ───────────────────────────────────────────────────────────────────
export const Spinner = ({ size = 16, className }: { size?: number; className?: string }) => (
  <Loader2 size={size} className={cn('animate-spin text-[var(--accent)]', className)} />
)

// ── Page loader ───────────────────────────────────────────────────────────────
export const PageLoader = () => (
  <div className="flex items-center justify-center h-64">
    <div className="text-center">
      <Spinner size={28} className="mx-auto mb-3" />
      <p className="text-xs text-[var(--muted)] font-mono uppercase tracking-widest">Loading</p>
    </div>
  </div>
)

// ── Empty state ────────────────────────────────────────────────────────────────
export const EmptyState = ({ message = 'No data found' }: { message?: string }) => (
  <div className="flex flex-col items-center justify-center py-16 text-center">
    <div className="w-12 h-12 rounded-full border border-[var(--border)] flex items-center justify-center mb-4">
      <span className="text-[var(--dim)] text-lg">—</span>
    </div>
    <p className="text-sm text-[var(--muted)]">{message}</p>
  </div>
)

// ── Modal ─────────────────────────────────────────────────────────────────────
interface ModalProps { open: boolean; onClose: () => void; title: string; children: ReactNode; width?: string }
export const Modal = ({ open, onClose, title, children, width = 'max-w-lg' }: ModalProps) => {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <div className={cn('relative card w-full animate-slide-up', width)}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--border)]">
          <h3 className="font-display text-base font-semibold">{title}</h3>
          <button onClick={onClose} className="text-[var(--muted)] hover:text-[var(--text)] transition-colors">
            <X size={18} />
          </button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  )
}

// ── Section header ─────────────────────────────────────────────────────────────
export const SectionHeader = ({ title, sub, children }: { title: string; sub?: string; children?: ReactNode }) => (
  <div className="flex items-start justify-between mb-6">
    <div>
      <h2 className="font-display text-xl font-semibold">{title}</h2>
      {sub && <p className="text-xs text-[var(--muted)] mt-0.5">{sub}</p>}
    </div>
    {children && <div className="flex items-center gap-2">{children}</div>}
  </div>
)

// ── Pagination ─────────────────────────────────────────────────────────────────
interface PaginationProps { page: number; total: number; pageSize: number; onChange: (p: number) => void }
export const Pagination = ({ page, total, pageSize, onChange }: PaginationProps) => {
  const totalPages = Math.ceil(total / pageSize)
  if (totalPages <= 1) return null
  return (
    <div className="flex items-center justify-between pt-4 border-t border-[var(--border)] mt-4">
      <p className="text-xs text-[var(--muted)] font-mono">
        {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, total)} of {total}
      </p>
      <div className="flex gap-1">
        <button onClick={() => onChange(page - 1)} disabled={page <= 1} className="btn btn-ghost btn-sm">← Prev</button>
        <button onClick={() => onChange(page + 1)} disabled={page >= totalPages} className="btn btn-ghost btn-sm">Next →</button>
      </div>
    </div>
  )
}

// ── Form Field wrapper ────────────────────────────────────────────────────────
export const Field = ({ label, children, error }: { label: string; children: ReactNode; error?: string }) => (
  <div className="space-y-1.5">
    <label className="erp-label">{label}</label>
    {children}
    {error && <p className="text-xs text-[var(--crimson)]">{error}</p>}
  </div>
)
