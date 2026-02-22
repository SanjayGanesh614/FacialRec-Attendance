// src/pages/admin/Dashboard.tsx
import { useQuery } from '@tanstack/react-query'
import { Users, UserCheck, UserX, Clock } from 'lucide-react'
import { attendanceApi, employeesApi } from '@/api'
import { StatCard, PageLoader, EmptyState, Avatar } from '@/components/ui'
import { statusBadgeClass, statusLabel, formatTime } from '@/utils'
import type { DailyAttendanceOut } from '@/types'

export const AdminDashboard = () => {
  const { data: todayData, isLoading: loadingToday } = useQuery({
    queryKey: ['attendance', 'today'],
    queryFn: attendanceApi.today,
    refetchInterval: 30_000, // refresh every 30s
  })

  const { data: employeesData } = useQuery({
    queryKey: ['employees', 'list', { page: 1, page_size: 1 }],
    queryFn: () => employeesApi.list({ page: 1, page_size: 1, is_active: true }),
  })

  const records = todayData ?? []
  const present  = records.filter(r => r.punch_in && !r.punch_out).length
  const out      = records.filter(r => r.punch_out).length
  const absent   = records.filter(r => !r.punch_in).length
  const late     = records.filter(r => r.is_late).length
  const total    = employeesData?.total ?? records.length

  // Sort: currently in > already left > absent
  const sorted = [...records].sort((a, b) => {
    const rank = (r: DailyAttendanceOut) =>
      r.punch_in && !r.punch_out ? 0 : r.punch_out ? 1 : 2
    return rank(a) - rank(b)
  })

  if (loadingToday) return <PageLoader />

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold">Dashboard</h1>
          <p className="text-xs text-[var(--muted)] mt-0.5">
            {new Date().toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
          </p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-[var(--emerald)] bg-[rgba(45,212,160,0.06)]">
          <div className="live-dot" />
          <span className="text-[10px] font-mono text-[var(--emerald)] tracking-wider">LIVE</span>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard label="In Office Now" value={present} sub={`of ${total} employees`} accent="green" icon={<UserCheck size={22} />} />
        <StatCard label="Checked Out" value={out} sub="left for the day" accent="amber" icon={<Users size={22} />} />
        <StatCard label="Not Yet In" value={absent} sub="no punch today" accent="red" icon={<UserX size={22} />} />
        <StatCard label="Late Arrivals" value={late} sub="past grace period" accent="sky" icon={<Clock size={22} />} />
      </div>

      {/* Today's attendance grid */}
      <div className="card">
        <div className="px-5 py-4 border-b border-[var(--border)] flex items-center justify-between">
          <div>
            <h2 className="font-display text-base font-semibold">Today's Attendance</h2>
            <p className="text-[11px] text-[var(--muted)] mt-0.5">{records.length} employees tracked</p>
          </div>
        </div>

        {records.length === 0 ? (
          <EmptyState message="No attendance data for today yet" />
        ) : (
          <div className="divide-y divide-[rgba(42,42,56,0.5)]">
            {sorted.map((record) => (
              <TodayRow key={record.id} record={record} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

const TodayRow = ({ record }: { record: DailyAttendanceOut }) => {
  const isIn = record.punch_in && !record.punch_out
  const isOut = !!record.punch_out
  const isAbsent = !record.punch_in

  return (
    <div className="flex items-center gap-4 px-5 py-3.5 hover:bg-[var(--bg-3)] transition-colors group animate-ticker">
      {/* Status indicator */}
      <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
        isIn ? 'bg-[var(--emerald)]' : isOut ? 'bg-[var(--muted)]' : 'bg-[var(--crimson)]'
      }`} />

      <Avatar name={record.employee_name} size="sm" />

      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-[var(--text)] truncate">{record.employee_name}</p>
      </div>

      <div className="flex items-center gap-6 text-xs font-mono text-[var(--muted)]">
        <span className="w-20 text-right">
          {record.punch_in ? formatTime(record.punch_in) : '—'}
        </span>
        <span className="w-20 text-right">
          {record.punch_out ? formatTime(record.punch_out) : isIn ? <span className="text-[var(--emerald)]">In office</span> : '—'}
        </span>
        <span className="w-14 text-right">
          {record.hours_worked ? `${record.hours_worked.toFixed(1)}h` : '—'}
        </span>
      </div>

      <span className={statusBadgeClass(record.status)}>
        {statusLabel(record.status)}
      </span>
    </div>
  )
}
