// src/pages/admin/Reports.tsx
// Phase 4 — Full Reports & Analytics
// Tabs: Overview | Daily EOD | Employee Drilldown | Departments

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  LineChart, Line, CartesianGrid, Cell,
} from 'recharts'
import { Download, TrendingUp, Calendar, Users, Building2 } from 'lucide-react'
import { reportsApi, attendanceApi, departmentsApi, employeesApi } from '@/api'
import { StatCard, PageLoader, EmptyState, Avatar } from '@/components/ui'
import { statusBadgeClass, statusLabel, formatTime, formatHours } from '@/utils'

const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
const CHART_TOOLTIP = {
  contentStyle: {
    background: '#1c1c24', border: '1px solid #2a2a38',
    borderRadius: 8, fontSize: 12,
    fontFamily: 'JetBrains Mono, monospace', color: '#e2e2ea',
  },
  cursor: { fill: 'rgba(201,168,76,0.05)' },
}

type Tab = 'overview' | 'daily' | 'employees' | 'departments'

export const ReportsPage = () => {
  const [tab, setTab] = useState<Tab>('overview')

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold">Reports & Analytics</h1>
        <p className="text-xs text-[var(--muted)] mt-0.5">Company-wide attendance insights and exports</p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 bg-[var(--bg-2)] border border-[var(--border)] rounded-xl p-1 w-fit">
        {([
          { key: 'overview',    label: 'Overview',    Icon: TrendingUp },
          { key: 'daily',       label: 'Daily EOD',   Icon: Calendar },
          { key: 'employees',   label: 'Employees',   Icon: Users },
          { key: 'departments', label: 'Departments', Icon: Building2 },
        ] as { key: Tab; label: string; Icon: React.FC<any> }[]).map(({ key, label, Icon }) => (
          <button key={key} onClick={() => setTab(key)}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              tab === key ? 'bg-[var(--accent)] text-[#0e0e12]' : 'text-[var(--muted)] hover:text-[var(--text)]'
            }`}
          >
            <Icon size={13} />{label}
          </button>
        ))}
      </div>

      <div className="animate-fade-in">
        {tab === 'overview'    && <OverviewTab />}
        {tab === 'daily'       && <DailyTab />}
        {tab === 'employees'   && <EmployeesTab />}
        {tab === 'departments' && <DepartmentsTab />}
      </div>
    </div>
  )
}

// ── Overview ───────────────────────────────────────────────────────────────────

const OverviewTab = () => {
  const now = new Date()
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [year, setYear]   = useState(now.getFullYear())

  const { data: summary, isLoading } = useQuery({
    queryKey: ['summary-all', month, year],
    queryFn: () => attendanceApi.summary({ month, year }),
  })
  const { data: trend } = useQuery({
    queryKey: ['trend-company'],
    queryFn: () => reportsApi.trend(undefined, 6),
  })
  const { data: deptData } = useQuery({
    queryKey: ['dept-comparison', month, year],
    queryFn: () => reportsApi.departments(month, year),
  })

  if (isLoading) return <PageLoader />

  return (
    <div className="space-y-6">
      <div className="flex justify-end gap-2">
        <select value={month} onChange={e => setMonth(Number(e.target.value))} className="erp-select">
          {MONTHS.map((m, i) => <option key={i} value={i+1}>{m}</option>)}
        </select>
        <select value={year} onChange={e => setYear(Number(e.target.value))} className="erp-select">
          {[2024,2025,2026].map(y => <option key={y} value={y}>{y}</option>)}
        </select>
      </div>

      {summary && (
        <div className="grid grid-cols-4 gap-4">
          <StatCard label="Attendance Rate"  value={`${summary.attendance_percentage}%`} accent="green" />
          <StatCard label="Days Present"     value={summary.days_present} sub={`of ${summary.total_working_days} working days`} />
          <StatCard label="Late Arrivals"    value={summary.days_late} accent="amber" />
          <StatCard label="Avg Hours / Day"  value={`${summary.average_hours_per_day}h`} accent="sky" />
        </div>
      )}

      <div className="grid grid-cols-2 gap-6">
        {/* 6-month trend */}
        <div className="card p-5">
          <h3 className="font-display text-sm font-semibold mb-0.5">6-Month Trend</h3>
          <p className="text-[10px] font-mono text-[var(--muted)] mb-4">Company-wide attendance rate</p>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={trend?.points ?? []} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2a38" vertical={false} />
              <XAxis dataKey="label" tick={{ fontSize: 10, fill: '#70708a', fontFamily: 'JetBrains Mono' }} />
              <YAxis domain={[0,100]} tickFormatter={v => `${v}%`} tick={{ fontSize: 10, fill: '#70708a', fontFamily: 'JetBrains Mono' }} />
              <Tooltip {...CHART_TOOLTIP} formatter={(v: number) => [`${v.toFixed(1)}%`, 'Attendance']} />
              <Line type="monotone" dataKey="attendance_pct" stroke="#c9a84c" strokeWidth={2.5}
                dot={{ fill: '#c9a84c', r: 4, strokeWidth: 0 }} activeDot={{ r: 6, strokeWidth: 0 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Monthly breakdown */}
        <div className="card p-5">
          <h3 className="font-display text-sm font-semibold mb-0.5">Monthly Breakdown</h3>
          <p className="text-[10px] font-mono text-[var(--muted)] mb-4">{MONTHS[month-1]} {year} — by status</p>
          {summary ? (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart layout="vertical" margin={{ left: 8 }}
                data={[
                  { label: 'Present', v: summary.days_present,  fill: '#2dd4a0' },
                  { label: 'Late',    v: summary.days_late,      fill: '#c9a84c' },
                  { label: 'Absent',  v: summary.days_absent,    fill: '#e05c6b' },
                  { label: 'WFH',     v: summary.days_wfh,       fill: '#5ba4e8' },
                ]}>
                <XAxis type="number" tick={{ fontSize: 10, fill: '#70708a', fontFamily: 'JetBrains Mono' }} />
                <YAxis type="category" dataKey="label" tick={{ fontSize: 11, fill: '#e2e2ea' }} width={52} />
                <Tooltip {...CHART_TOOLTIP} formatter={(v: number) => [v, 'Days']} />
                <Bar dataKey="v" radius={[0,4,4,0]}>
                  {['#2dd4a0','#c9a84c','#e05c6b','#5ba4e8'].map((c, i) => <Cell key={i} fill={c} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : <EmptyState />}
        </div>
      </div>

      {/* Dept comparison */}
      {(deptData?.departments?.length ?? 0) > 0 && (
        <div className="card p-5">
          <h3 className="font-display text-sm font-semibold mb-0.5">Department Comparison</h3>
          <p className="text-[10px] font-mono text-[var(--muted)] mb-5">{MONTHS[month-1]} {year} — attendance rate per department</p>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={deptData!.departments.map((d: any) => ({ name: d.department_code, pct: d.attendance_pct, full: d.department_name }))}
              margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2a38" vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#70708a', fontFamily: 'JetBrains Mono' }} />
              <YAxis domain={[0,100]} tickFormatter={v => `${v}%`} tick={{ fontSize: 10, fill: '#70708a', fontFamily: 'JetBrains Mono' }} />
              <Tooltip {...CHART_TOOLTIP} formatter={(v: number, _, p) => [`${v}%`, p.payload.full]} />
              <Bar dataKey="pct" fill="#c9a84c" radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}

// ── Daily EOD ──────────────────────────────────────────────────────────────────

const DailyTab = () => {
  const today = new Date().toISOString().split('T')[0]
  const [date, setDate]     = useState(today)
  const [deptId, setDeptId] = useState('')

  const { data: depts } = useQuery({ queryKey: ['departments'], queryFn: departmentsApi.list })
  const { data, isLoading } = useQuery({
    queryKey: ['daily-report', date, deptId],
    queryFn: () => reportsApi.daily(date, deptId || undefined),
  })

  return (
    <div className="space-y-5">
      <div className="flex items-end gap-3">
        <div>
          <label className="erp-label">Date</label>
          <input type="date" value={date} onChange={e => setDate(e.target.value)} className="erp-input" max={today} />
        </div>
        <div>
          <label className="erp-label">Department</label>
          <select value={deptId} onChange={e => setDeptId(e.target.value)} className="erp-select">
            <option value="">All Departments</option>
            {depts?.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
        </div>
        <button onClick={() => reportsApi.exportCsv(date, date, undefined, deptId || undefined)} className="btn btn-ghost mb-0.5">
          <Download size={13} /> Export CSV
        </button>
      </div>

      {data && (
        <div className="grid grid-cols-5 gap-3">
          {[
            { label: 'Total',   value: data.total_employees, accent: 'amber' },
            { label: 'Present', value: data.present,         accent: 'green' },
            { label: 'Absent',  value: data.absent,          accent: 'red'   },
            { label: 'Late',    value: data.late,            accent: 'sky'   },
            { label: 'Rate',    value: `${data.attendance_pct}%`, accent: 'green' },
          ].map(s => (
            <div key={s.label} className={`card p-4 card-accent-${s.accent}`}>
              <p className="text-[10px] font-mono text-[var(--muted)] uppercase tracking-widest mb-1">{s.label}</p>
              <p className="font-display text-2xl font-semibold">{s.value}</p>
            </div>
          ))}
        </div>
      )}

      <div className="card">
        {isLoading ? <PageLoader /> : !data?.rows?.length ? <EmptyState message="No records for this date" /> : (
          <table className="erp-table">
            <thead>
              <tr>
                <th>Employee</th>
                <th>Department</th>
                <th>Punch In</th>
                <th>Punch Out</th>
                <th>Hours</th>
                <th>Late By</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {data.rows.map((r: any) => (
                <tr key={r.employee_id}>
                  <td>
                    <div className="flex items-center gap-2.5">
                      <Avatar name={r.employee_name} size="sm" />
                      <div>
                        <p className="font-medium text-sm">{r.employee_name}</p>
                        <p className="text-[10px] font-mono text-[var(--muted)]">{r.employee_code}</p>
                      </div>
                    </div>
                  </td>
                  <td className="text-xs text-[var(--muted)]">{r.department_name ?? '—'}</td>
                  <td className="font-mono text-xs">{formatTime(r.punch_in)}</td>
                  <td className="font-mono text-xs">{formatTime(r.punch_out)}</td>
                  <td className="font-mono text-xs">{formatHours(r.hours_worked)}</td>
                  <td className="font-mono text-xs text-[var(--muted)]">
                    {r.late_by_minutes > 0 ? `${r.late_by_minutes}m` : '—'}
                  </td>
                  <td>
                    <span className={statusBadgeClass(r.status)}>{statusLabel(r.status)}</span>
                    {r.is_corrected && <span className="ml-1.5 text-[9px] font-mono text-[var(--accent)]">EDITED</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

// ── Employee Drilldown ─────────────────────────────────────────────────────────

const EmployeesTab = () => {
  const now = new Date()
  const [empSearch, setEmpSearch]   = useState('')
  const [selectedEmp, setSelectedEmp] = useState<any>(null)
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [year,  setYear]  = useState(now.getFullYear())

  const { data: empList } = useQuery({
    queryKey: ['employees-search', empSearch],
    queryFn: () => employeesApi.list({ page: 1, page_size: 10, search: empSearch || undefined }),
  })

  const { data: report, isLoading: reportLoading } = useQuery({
    queryKey: ['monthly-report', selectedEmp?.id, month, year],
    queryFn: () => reportsApi.monthly(selectedEmp!.id, month, year),
    enabled: !!selectedEmp,
  })

  const { data: trend } = useQuery({
    queryKey: ['trend-emp', selectedEmp?.id],
    queryFn: () => reportsApi.trend(selectedEmp!.id, 6),
    enabled: !!selectedEmp,
  })

  const exportEmpCsv = () => {
    if (!selectedEmp) return
    const from = `${year}-${String(month).padStart(2,'0')}-01`
    const to   = `${year}-${String(month).padStart(2,'0')}-${new Date(year, month, 0).getDate()}`
    reportsApi.exportCsv(from, to, selectedEmp.id)
  }

  return (
    <div className="grid grid-cols-3 gap-6">
      {/* Employee picker sidebar */}
      <div className="card p-4 space-y-3 self-start">
        <p className="text-[10px] font-mono uppercase tracking-widest text-[var(--muted)]">Select Employee</p>
        <input className="erp-input text-xs" placeholder="Search name or code…"
          value={empSearch} onChange={e => setEmpSearch(e.target.value)} />
        <div className="space-y-1 max-h-96 overflow-y-auto">
          {empList?.items.map((emp: any) => (
            <button key={emp.id} onClick={() => setSelectedEmp(emp)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all ${
                selectedEmp?.id === emp.id
                  ? 'bg-[rgba(201,168,76,0.12)] border border-[rgba(201,168,76,0.25)]'
                  : 'hover:bg-[var(--bg-3)]'
              }`}>
              <Avatar name={emp.full_name} size="sm" />
              <div className="min-w-0">
                <p className="text-sm font-medium truncate">{emp.full_name}</p>
                <p className="text-[10px] font-mono text-[var(--muted)]">{emp.employee_code}</p>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Report panel */}
      <div className="col-span-2 space-y-4">
        {!selectedEmp ? (
          <div className="card h-64 flex items-center justify-center">
            <EmptyState message="Select an employee to view their report" />
          </div>
        ) : reportLoading ? <PageLoader /> : !report ? <EmptyState /> : (
          <>
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-display text-base font-semibold">{report.employee_name}</h3>
                <p className="text-xs text-[var(--muted)]">{report.department_name ?? 'No department'} · {report.employee_code}</p>
              </div>
              <div className="flex gap-2">
                <select value={month} onChange={e => setMonth(Number(e.target.value))} className="erp-select">
                  {MONTHS.map((m, i) => <option key={i} value={i+1}>{m}</option>)}
                </select>
                <select value={year} onChange={e => setYear(Number(e.target.value))} className="erp-select">
                  {[2024,2025,2026].map(y => <option key={y} value={y}>{y}</option>)}
                </select>
                <button onClick={exportEmpCsv} className="btn btn-ghost btn-sm">
                  <Download size={12} /> CSV
                </button>
              </div>
            </div>

            {/* KPI grid */}
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: 'Attendance', value: `${report.attendance_pct}%`, accent: 'green'  as const },
                { label: 'Present Days', value: report.days_present },
                { label: 'Late Days',  value: report.days_late, accent: 'amber' as const },
                { label: 'Absent',     value: report.days_absent, accent: 'red'  as const },
                { label: 'Total Hours', value: `${report.total_hours}h` },
                { label: 'Avg Hrs/Day', value: `${report.average_hours}h`, accent: 'sky' as const },
              ].map(s => (
                <div key={s.label} className={`card p-3 card-accent-${s.accent ?? 'amber'}`}>
                  <p className="text-[9px] font-mono text-[var(--muted)] uppercase tracking-widest mb-1">{s.label}</p>
                  <p className="font-display text-xl font-semibold">{s.value}</p>
                </div>
              ))}
            </div>

            {/* Calendar heatmap */}
            <MonthHeatmap report={report} />

            {/* Trend line */}
            {trend && (
              <div className="card p-4">
                <h4 className="text-[10px] font-mono uppercase tracking-widest text-[var(--muted)] mb-3">6-Month Attendance Trend</h4>
                <ResponsiveContainer width="100%" height={150}>
                  <LineChart data={trend.points} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#2a2a38" vertical={false} />
                    <XAxis dataKey="label" tick={{ fontSize: 9, fill: '#70708a', fontFamily: 'JetBrains Mono' }} />
                    <YAxis domain={[0,100]} tickFormatter={v => `${v}%`} tick={{ fontSize: 9, fill: '#70708a', fontFamily: 'JetBrains Mono' }} />
                    <Tooltip {...CHART_TOOLTIP} formatter={(v: number) => [`${v.toFixed(1)}%`, 'Attendance']} />
                    <Line type="monotone" dataKey="attendance_pct" stroke="#c9a84c" strokeWidth={2}
                      dot={{ fill: '#c9a84c', r: 3, strokeWidth: 0 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

// Month heatmap component
const MonthHeatmap = ({ report }: { report: any }) => {
  const { year, month, days } = report
  const firstDow    = new Date(year, month - 1, 1).getDay()
  const daysInMonth = new Date(year, month, 0).getDate()
  const dayMap      = new Map(days.map((d: any) => [d.date, d]))
  const todayStr    = new Date().toISOString().split('T')[0]
  const STATUS_COLOR: Record<string, string> = {
    present: '#2dd4a0', late: '#c9a84c', absent: '#e05c6b',
    wfh: '#5ba4e8', half_day: '#c9a84c', leave: '#5ba4e8',
  }

  return (
    <div className="card p-4">
      <p className="text-[10px] font-mono text-[var(--muted)] uppercase tracking-widest mb-3">
        {MONTHS[month-1]} {year} — Day-by-Day
      </p>
      <div className="grid grid-cols-7 gap-1 mb-1">
        {['Su','Mo','Tu','We','Th','Fr','Sa'].map(d => (
          <div key={d} className="text-center text-[9px] font-mono text-[var(--dim)]">{d}</div>
        ))}
      </div>
      <div className="grid grid-cols-7 gap-1">
        {Array.from({ length: firstDow }).map((_, i) => <div key={`b${i}`} />)}
        {Array.from({ length: daysInMonth }, (_, i) => {
          const day     = i + 1
          const dateStr = `${year}-${String(month).padStart(2,'0')}-${String(day).padStart(2,'0')}`
          const rec     = dayMap.get(dateStr) as any
          const isWeekend = [0,6].includes(new Date(dateStr).getDay())
          const isFuture  = dateStr > todayStr
          const bg = rec ? (STATUS_COLOR[rec.status] ?? '#525268')
                  : isWeekend ? '#1c1c24'
                  : isFuture  ? 'transparent'
                  : '#e05c6b'

          return (
            <div key={day}
              title={rec ? `${rec.status} · ${formatTime(rec.punch_in)} – ${formatTime(rec.punch_out)}` : dateStr}
              className="aspect-square rounded flex items-center justify-center cursor-default"
              style={{ background: bg, opacity: (isWeekend || isFuture) ? 0.25 : 1 }}
            >
              <span style={{ color: isFuture ? '#525268' : '#0e0e12', fontSize: 8, fontFamily: 'JetBrains Mono', opacity: 0.8 }}>
                {day}
              </span>
            </div>
          )
        })}
      </div>
      <div className="flex gap-4 mt-3 pt-3 border-t border-[var(--border)]">
        {[['present','#2dd4a0'],['late','#c9a84c'],['absent','#e05c6b'],['wfh','#5ba4e8']].map(([s,c]) => (
          <div key={s} className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-sm" style={{ background: c }} />
            <span className="text-[9px] text-[var(--muted)] capitalize">{s}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Departments ────────────────────────────────────────────────────────────────

const DepartmentsTab = () => {
  const now = new Date()
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [year,  setYear]  = useState(now.getFullYear())

  const { data, isLoading } = useQuery({
    queryKey: ['dept-comparison', month, year],
    queryFn: () => reportsApi.departments(month, year),
  })

  const depts: any[] = data?.departments ?? []

  return (
    <div className="space-y-5">
      <div className="flex gap-2">
        <select value={month} onChange={e => setMonth(Number(e.target.value))} className="erp-select">
          {MONTHS.map((m, i) => <option key={i} value={i+1}>{m}</option>)}
        </select>
        <select value={year} onChange={e => setYear(Number(e.target.value))} className="erp-select">
          {[2024,2025,2026].map(y => <option key={y} value={y}>{y}</option>)}
        </select>
      </div>

      {isLoading ? <PageLoader /> : depts.length === 0 ? <EmptyState message="No department data for this period" /> : (
        <>
          {/* Dual-axis bar chart */}
          <div className="card p-5">
            <h3 className="font-display text-sm font-semibold mb-0.5">Attendance Rate by Department</h3>
            <p className="text-[10px] font-mono text-[var(--muted)] mb-5">{MONTHS[month-1]} {year}</p>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart
                data={depts.map(d => ({
                  name: d.department_code, full: d.department_name,
                  pct: d.attendance_pct, hours: d.average_hours,
                }))}
                margin={{ top: 4, right: 40, bottom: 8, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a2a38" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#70708a', fontFamily: 'JetBrains Mono' }} />
                <YAxis yAxisId="pct" orientation="left" domain={[0,100]}
                  tickFormatter={v => `${v}%`} tick={{ fontSize: 10, fill: '#70708a', fontFamily: 'JetBrains Mono' }} />
                <YAxis yAxisId="hrs" orientation="right"
                  tickFormatter={v => `${v}h`} tick={{ fontSize: 10, fill: '#70708a', fontFamily: 'JetBrains Mono' }} />
                <Tooltip {...CHART_TOOLTIP}
                  formatter={(v: number, name: string, p: any) =>
                    name === 'pct' ? [`${v}%`, `${p.payload.full} — Attendance`] : [`${v}h`, `${p.payload.full} — Avg Hours`]} />
                <Bar yAxisId="pct" dataKey="pct" fill="#c9a84c" radius={[4,4,0,0]} name="pct" />
                <Bar yAxisId="hrs" dataKey="hours" fill="#5ba4e8" radius={[4,4,0,0]} name="hrs" />
              </BarChart>
            </ResponsiveContainer>
            <div className="flex gap-5 mt-3 justify-center">
              {[['Attendance Rate','#c9a84c'],['Avg Hours / Day','#5ba4e8']].map(([l,c]) => (
                <div key={l} className="flex items-center gap-1.5">
                  <div className="w-3 h-2 rounded-sm" style={{ background: c }} />
                  <span className="text-[10px] text-[var(--muted)]">{l}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Table */}
          <div className="card">
            <table className="erp-table">
              <thead>
                <tr>
                  <th>Department</th>
                  <th>Headcount</th>
                  <th>Days Present</th>
                  <th>Days Late</th>
                  <th>Days Absent</th>
                  <th>Avg Hours</th>
                  <th>Attendance %</th>
                </tr>
              </thead>
              <tbody>
                {[...depts].sort((a,b) => b.attendance_pct - a.attendance_pct).map((d: any) => (
                  <tr key={d.department_id}>
                    <td>
                      <p className="font-medium text-sm">{d.department_name}</p>
                      <p className="text-[10px] font-mono text-[var(--muted)]">{d.department_code}</p>
                    </td>
                    <td className="font-mono text-sm">{d.employee_count}</td>
                    <td className="font-mono text-sm text-[var(--emerald)]">{d.days_present}</td>
                    <td className="font-mono text-sm text-[var(--accent)]">{d.days_late}</td>
                    <td className="font-mono text-sm text-[var(--crimson)]">{d.days_absent}</td>
                    <td className="font-mono text-sm">{d.average_hours}h</td>
                    <td>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-1.5 bg-[var(--bg-4)] rounded-full overflow-hidden">
                          <div className="h-full rounded-full transition-all" style={{
                            width: `${d.attendance_pct}%`,
                            background: d.attendance_pct >= 90 ? '#2dd4a0' : d.attendance_pct >= 75 ? '#c9a84c' : '#e05c6b'
                          }} />
                        </div>
                        <span className="font-mono text-xs w-12 text-right">{d.attendance_pct}%</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
