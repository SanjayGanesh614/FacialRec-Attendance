// src/pages/employee/MyDashboard.tsx
import { useQuery } from '@tanstack/react-query'
import { attendanceApi, reportsApi } from '@/api'
import { useAuthStore } from '@/store/authStore'
import { StatCard, PageLoader, Avatar } from '@/components/ui'
import { statusBadgeClass, statusLabel, formatTime, formatHours } from '@/utils'
import { RadialBarChart, RadialBar, ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts'

export const MyDashboard = () => {
  const { user } = useAuthStore()
  const now = new Date()

  const { data: summary, isLoading: loadingSum } = useQuery({
    queryKey: ['my-summary', now.getMonth(), now.getFullYear()],
    queryFn: () => attendanceApi.summary({ month: now.getMonth() + 1, year: now.getFullYear() }),
  })

  const { data: trend } = useQuery({
    queryKey: ['my-trend', user?.id],
    queryFn: () => reportsApi.trend(user!.id, 6),
    enabled: !!user?.id,
  })

  const { data: todayData, isLoading: loadingToday } = useQuery({
    queryKey: ['attendance', 'today'],
    queryFn: attendanceApi.today,
    refetchInterval: 60_000,
  })

  const myToday = todayData?.find(r => r.employee_name === user?.full_name)

  if (loadingSum || loadingToday) return <PageLoader />

  const attPct = summary?.attendance_percentage ?? 0

  return (
    <div className="space-y-8">
      {/* Welcome header */}
      <div className="flex items-center gap-4">
        <Avatar name={user?.full_name ?? '?'} size="lg" />
        <div>
          <h1 className="font-display text-2xl font-semibold">
            Good {now.getHours() < 12 ? 'morning' : now.getHours() < 17 ? 'afternoon' : 'evening'}, {user?.full_name.split(' ')[0]}
          </h1>
          <p className="text-xs text-[var(--muted)] mt-0.5">
            {now.toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long' })} · {user?.department_name ?? 'No department'}
          </p>
        </div>
      </div>

      {/* Today's status card */}
      <div className="card p-5 border-l-2 border-l-[var(--accent)]">
        <p className="text-[10px] font-mono uppercase tracking-widest text-[var(--muted)] mb-3">Today's Status</p>
        {myToday ? (
          <div className="flex items-center gap-8">
            <span className={statusBadgeClass(myToday.status)}>
              {statusLabel(myToday.status)}
            </span>
            <div className="flex gap-8 text-sm">
              <div>
                <p className="text-[10px] font-mono text-[var(--muted)] uppercase mb-0.5">Punched In</p>
                <p className="font-mono text-base">{formatTime(myToday.punch_in)}</p>
              </div>
              {myToday.punch_out && (
                <div>
                  <p className="text-[10px] font-mono text-[var(--muted)] uppercase mb-0.5">Punched Out</p>
                  <p className="font-mono text-base">{formatTime(myToday.punch_out)}</p>
                </div>
              )}
              {myToday.hours_worked > 0 && (
                <div>
                  <p className="text-[10px] font-mono text-[var(--muted)] uppercase mb-0.5">Hours Today</p>
                  <p className="font-mono text-base">{formatHours(myToday.hours_worked)}</p>
                </div>
              )}
              {myToday.is_late && (
                <div>
                  <p className="text-[10px] font-mono text-[var(--muted)] uppercase mb-0.5">Late By</p>
                  <p className="font-mono text-base text-[var(--accent)]">{myToday.late_by_minutes}m</p>
                </div>
              )}
            </div>
          </div>
        ) : (
          <p className="text-sm text-[var(--muted)]">No attendance recorded today — visit the terminal to punch in.</p>
        )}
      </div>

      {/* Month stats */}
      <div className="grid grid-cols-3 gap-4">
        <StatCard label="This Month" value={`${attPct}%`} sub="Attendance rate" accent="green" />
        <StatCard label="Days Present" value={summary?.days_present ?? 0} sub={`of ${summary?.total_working_days ?? 0} working days`} />
        <StatCard label="Late Arrivals" value={summary?.days_late ?? 0} sub="this month" accent="amber" />
      </div>

      {/* Radial attendance gauge */}
      <div className="card p-5">
        <p className="text-[10px] font-mono uppercase tracking-widest text-[var(--muted)] mb-1">Monthly Attendance Rate</p>
        <p className="font-display text-sm text-[var(--muted)] mb-4">{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][now.getMonth()]} {now.getFullYear()}</p>
        <div className="flex items-center gap-8">
          <div className="relative">
            <ResponsiveContainer width={160} height={160}>
              <RadialBarChart
                innerRadius={50} outerRadius={70}
                data={[{ value: attPct, fill: attPct >= 90 ? '#2dd4a0' : attPct >= 75 ? '#c9a84c' : '#e05c6b' }]}
                startAngle={90} endAngle={90 - (3.6 * attPct)}
              >
                <RadialBar dataKey="value" background={{ fill: '#1c1c24' }} cornerRadius={4} />
              </RadialBarChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="font-display text-2xl font-semibold">{attPct}%</span>
            </div>
          </div>
          <div className="space-y-3">
            {[
              { label: 'Days Present', val: summary?.days_present, color: 'var(--emerald)' },
              { label: 'Days Absent', val: summary?.days_absent, color: 'var(--crimson)' },
              { label: 'WFH Days', val: summary?.days_wfh, color: 'var(--sky)' },
              { label: 'Avg Hours/Day', val: `${summary?.average_hours_per_day ?? 0}h`, color: 'var(--accent)' },
            ].map(({ label, val, color }) => (
              <div key={label} className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: color }} />
                <span className="text-xs text-[var(--muted)] w-28">{label}</span>
                <span className="font-mono text-sm">{val}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Personal 6-month trend */}
      {trend && (
        <div className="card p-5">
          <p className="text-[10px] font-mono text-[var(--muted)] uppercase tracking-widest mb-1">My 6-Month Attendance Trend</p>
          <p className="font-display text-sm text-[var(--muted)] mb-4">How your attendance rate has changed over time</p>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={trend.points} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2a38" vertical={false} />
              <XAxis dataKey="label" tick={{ fontSize: 10, fill: '#70708a', fontFamily: 'JetBrains Mono' }} />
              <YAxis domain={[0, 100]} tickFormatter={(v: number) => `${v}%`}
                tick={{ fontSize: 10, fill: '#70708a', fontFamily: 'JetBrains Mono' }} />
              <Tooltip
                contentStyle={{ background: '#1c1c24', border: '1px solid #2a2a38', borderRadius: 8, fontSize: 12, fontFamily: 'JetBrains Mono', color: '#e2e2ea' }}
                formatter={(v: number) => [`${v.toFixed(1)}%`, 'Attendance']}
              />
              <Line type="monotone" dataKey="attendance_pct" stroke="#c9a84c" strokeWidth={2.5}
                dot={{ fill: '#c9a84c', r: 4, strokeWidth: 0 }}
                activeDot={{ r: 6, strokeWidth: 0 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
