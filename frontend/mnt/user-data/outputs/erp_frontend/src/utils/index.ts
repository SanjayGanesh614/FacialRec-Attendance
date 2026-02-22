// src/utils/index.ts
import { clsx, type ClassValue } from 'clsx'
import type { DailyStatus } from '@/types'

export const cn = (...inputs: ClassValue[]) => clsx(inputs)

export const statusBadgeClass = (status: DailyStatus): string => ({
  present:  'badge badge-present',
  absent:   'badge badge-absent',
  late:     'badge badge-late',
  wfh:      'badge badge-wfh',
  half_day: 'badge badge-half',
  leave:    'badge badge-wfh',
  holiday:  'badge badge-half',
}[status] ?? 'badge')

export const statusLabel = (status: DailyStatus): string => ({
  present:  'Present',
  absent:   'Absent',
  late:     'Late',
  wfh:      'WFH',
  half_day: 'Half Day',
  leave:    'Leave',
  holiday:  'Holiday',
}[status] ?? status)

export const formatTime = (t: string | null): string => {
  if (!t) return '—'
  const [h, m] = t.split(':')
  const hour = parseInt(h)
  const ampm = hour >= 12 ? 'PM' : 'AM'
  const h12 = hour % 12 || 12
  return `${h12}:${m} ${ampm}`
}

export const formatHours = (h: number): string => {
  if (!h) return '—'
  const hrs = Math.floor(h)
  const mins = Math.round((h - hrs) * 60)
  return mins ? `${hrs}h ${mins}m` : `${hrs}h`
}

export const formatDate = (d: string): string => {
  return new Date(d).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric'
  })
}

export const roleLabel = (role: string): string => ({
  super_admin: 'Super Admin',
  manager: 'Manager',
  employee: 'Employee',
}[role] ?? role)

export const getInitials = (name: string): string =>
  name.split(' ').slice(0, 2).map(n => n[0]).join('').toUpperCase()

export const pct = (n: number) => `${n.toFixed(1)}%`
