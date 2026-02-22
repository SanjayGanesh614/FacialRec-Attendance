// src/pages/employee/MyHistory.tsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { attendanceApi } from '@/api'
import { PageLoader, EmptyState, Pagination } from '@/components/ui'
import { statusBadgeClass, statusLabel, formatTime, formatHours, formatDate } from '@/utils'

const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

export const MyHistory = () => {
  const [page, setPage] = useState(1)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo]     = useState('')
  const [view, setView] = useState<'table' | 'calendar'>('table')

  const now = new Date()
  const [calMonth, setCalMonth] = useState(now.getMonth())
  const [calYear,  setCalYear]  = useState(now.getFullYear())

  const { data, isLoading } = useQuery({
    queryKey: ['my-attendance', page, dateFrom, dateTo],
    queryFn: () => attendanceApi.mine({ page, date_from: dateFrom || undefined, date_to: dateTo || undefined }),
    placeholderData: p => p,
  })

  // For calendar view — fetch the whole month at once
  const firstOfMonth = `${calYear}-${String(calMonth + 1).padStart(2, '0')}-01`
  const lastDay = new Date(calYear, calMonth + 1, 0).getDate()
  const lastOfMonth = `${calYear}-${String(calMonth + 1).padStart(2, '0')}-${lastDay}`

  const { data: calData } = useQuery({
    queryKey: ['my-attendance', 'calendar', calMonth, calYear],
    queryFn: () => attendanceApi.mine({ page: 1, page_size: 31, date_from: firstOfMonth, date_to: lastOfMonth }),
    enabled: view === 'calendar',
  })

  const dayMap = new Map(calData?.items.map(r => [r.date, r]))

  // Build calendar grid
  const firstDow = new Date(calYear, calMonth, 1).getDay() // 0=Sun
  const totalDays = new Date(calYear, calMonth + 1, 0).getDate()

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold">My Attendance</h1>
          <p className="text-xs text-[var(--muted)] mt-0.5">Your personal attendance history</p>
        </div>
        <div className="flex gap-1 bg-[var(--bg-3)] border border-[var(--border)] rounded-lg p-1">
          {(['table', 'calendar'] as const).map(v => (
            <button key={v} onClick={() => setView(v)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${view === v ? 'bg-[var(--accent)] text-[#0e0e12]' : 'text-[var(--muted)] hover:text-[var(--text)]'}`}>
              {v.charAt(0).toUpperCase() + v.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {view === 'table' ? (
        <>
          {/* Filters */}
          <div className="flex gap-3">
            <div>
              <label className="erp-label">From</label>
              <input type="date" value={dateFrom} onChange={e => { setDateFrom(e.target.value); setPage(1) }} className="erp-input" />
            </div>
            <div>
              <label className="erp-label">To</label>
              <input type="date" value={dateTo} onChange={e => { setDateTo(e.target.value); setPage(1) }} className="erp-input" />
            </div>
          </div>

          <div className="card">
            {isLoading ? <PageLoader /> : data?.items.length === 0 ? <EmptyState message="No records found" /> : (
              <>
                <table className="erp-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Punch In</th>
                      <th>Punch Out</th>
                      <th>Hours</th>
                      <th>Late By</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data?.items.map(r => (
                      <tr key={r.id}>
                        <td className="font-mono text-xs">{formatDate(r.date)}</td>
                        <td className="font-mono text-xs">{formatTime(r.punch_in)}</td>
                        <td className="font-mono text-xs">{formatTime(r.punch_out)}</td>
                        <td className="font-mono text-xs">{formatHours(r.hours_worked)}</td>
                        <td className="font-mono text-xs text-[var(--muted)]">
                          {r.late_by_minutes > 0 ? `${r.late_by_minutes}m` : '—'}
                        </td>
                        <td><span className={statusBadgeClass(r.status)}>{statusLabel(r.status)}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div className="px-5 pb-4">
                  <Pagination page={page} total={data?.total ?? 0} pageSize={31} onChange={setPage} />
                </div>
              </>
            )}
          </div>
        </>
      ) : (
        /* Calendar view */
        <div className="card p-5">
          {/* Month nav */}
          <div className="flex items-center justify-between mb-5">
            <button
              onClick={() => { const d = new Date(calYear, calMonth - 1); setCalMonth(d.getMonth()); setCalYear(d.getFullYear()) }}
              className="btn btn-ghost btn-sm">← Prev</button>
            <h3 className="font-display text-base font-semibold">{MONTHS[calMonth]} {calYear}</h3>
            <button
              onClick={() => { const d = new Date(calYear, calMonth + 1); setCalMonth(d.getMonth()); setCalYear(d.getFullYear()) }}
              className="btn btn-ghost btn-sm">Next →</button>
          </div>

          {/* Day headers */}
          <div className="grid grid-cols-7 mb-2">
            {['Sun','Mon','Tue','Wed','Thu','Fri','Sat'].map(d => (
              <div key={d} className="text-center text-[10px] font-mono text-[var(--muted)] py-1">{d}</div>
            ))}
          </div>

          {/* Calendar grid */}
          <div className="grid grid-cols-7 gap-1">
            {/* Empty cells for offset */}
            {Array.from({ length: firstDow }).map((_, i) => <div key={`empty-${i}`} />)}

            {/* Day cells */}
            {Array.from({ length: totalDays }, (_, i) => {
              const day = i + 1
              const dateStr = `${calYear}-${String(calMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
              const record = dayMap.get(dateStr)
              const isToday = dateStr === new Date().toISOString().split('T')[0]
              const isFuture = new Date(dateStr) > new Date()
              const isWeekend = new Date(dateStr).getDay() === 0 || new Date(dateStr).getDay() === 6

              const cellColor = record
                ? { present: 'bg-[rgba(45,212,160,0.15)] border-[rgba(45,212,160,0.3)] text-[var(--emerald)]',
                    late:    'bg-[rgba(201,168,76,0.12)] border-[rgba(201,168,76,0.3)] text-[var(--accent)]',
                    absent:  'bg-[rgba(224,92,107,0.1)] border-[rgba(224,92,107,0.2)] text-[var(--crimson)]',
                    wfh:     'bg-[rgba(91,164,232,0.1)] border-[rgba(91,164,232,0.2)] text-[var(--sky)]',
                  }[record.status] ?? 'bg-[var(--bg-3)] border-[var(--border)] text-[var(--muted)]'
                : isFuture
                  ? 'bg-transparent border-transparent text-[var(--dim)]'
                  : isWeekend
                    ? 'bg-[var(--bg-3)] border-[var(--border)] text-[var(--dim)]'
                    : 'bg-[rgba(224,92,107,0.05)] border-[rgba(224,92,107,0.1)] text-[var(--crimson)]'

              return (
                <div
                  key={day}
                  className={`relative border rounded-lg p-2 text-center transition-all cursor-default ${cellColor} ${isToday ? 'ring-1 ring-[var(--accent)]' : ''}`}
                  title={record ? `${statusLabel(record.status)} · ${formatTime(record.punch_in)} → ${formatTime(record.punch_out)}` : undefined}
                >
                  <span className="text-xs font-mono">{day}</span>
                  {record && (
                    <div className="text-[8px] font-mono mt-0.5 opacity-70 truncate">
                      {statusLabel(record.status)}
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {/* Legend */}
          <div className="flex items-center gap-4 mt-4 pt-4 border-t border-[var(--border)]">
            {[
              { label: 'Present', cls: 'bg-[var(--emerald)]' },
              { label: 'Late',    cls: 'bg-[var(--accent)]' },
              { label: 'Absent',  cls: 'bg-[var(--crimson)]' },
              { label: 'WFH',     cls: 'bg-[var(--sky)]' },
              { label: 'Weekend', cls: 'bg-[var(--border-l)]' },
            ].map(({ label, cls }) => (
              <div key={label} className="flex items-center gap-1.5">
                <div className={`w-2.5 h-2.5 rounded-sm ${cls}`} />
                <span className="text-[10px] text-[var(--muted)]">{label}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
