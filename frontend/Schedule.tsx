// src/pages/admin/Schedule.tsx
// ─────────────────────────────────────────────────────────────
// Admin schedule management:
//   Left: Week calendar grid — who is planning office/WFH/leave
//         each day. Navigate weeks. Filter by department.
//   Right panel: Tag mandatory attendance for selected day.
//         Pick employees or entire department, set cutoff time.
// ─────────────────────────────────────────────────────────────

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Building2, Home, Palmtree, Lock, ChevronLeft, ChevronRight,
  AlertTriangle, Users, X, Check
} from 'lucide-react'
import toast from 'react-hot-toast'
import { format, startOfWeek, addWeeks, subWeeks, addDays, isToday } from 'date-fns'
import { scheduleApi, departmentsApi, employeesApi } from '@/api'
import { PageLoader, Spinner, Avatar } from '@/components/ui'

const INTENT_COLORS: Record<string, string> = {
  office: 'text-[var(--emerald)] bg-[rgba(45,212,160,0.1)]',
  wfh:    'text-[var(--sky)] bg-[rgba(91,164,232,0.1)]',
  leave:  'text-[var(--accent)] bg-[rgba(201,168,76,0.1)]',
}
const INTENT_ICONS: Record<string, React.FC<{ size?: number }>> = {
  office: Building2, wfh: Home, leave: Palmtree,
}

export const SchedulePage = () => {
  const qc = useQueryClient()
  const [weekOf, setWeekOf] = useState(() => startOfWeek(new Date(), { weekStartsOn: 1 }))
  const [deptFilter, setDeptFilter] = useState('')
  const [selectedDay, setSelectedDay] = useState<string | null>(null)
  const [mandateEmpIds, setMandateEmpIds] = useState<string[]>([])
  const [mandateDept, setMandateDept] = useState('')
  const [cutoff, setCutoff] = useState('10:30')
  const [mandateNote, setMandateNote] = useState('')

  const weekStart = format(weekOf, 'yyyy-MM-dd')
  const weekDays  = Array.from({ length: 5 }, (_, i) => addDays(weekOf, i))

  const { data: weekData, isLoading } = useQuery({
    queryKey: ['schedule', 'week', weekStart, deptFilter],
    queryFn: () => scheduleApi.weekSummary(weekStart, deptFilter || undefined),
  })

  const { data: depts } = useQuery({ queryKey: ['departments'], queryFn: departmentsApi.list })

  const { data: employees } = useQuery({
    queryKey: ['employees', 'all', deptFilter],
    queryFn: () => employeesApi.list({ page: 1, page_size: 200, department_id: deptFilter || undefined }),
  })

  const { mutate: mandate, isPending: mandating } = useMutation({
    mutationFn: () => scheduleApi.mandate({
      date: selectedDay!,
      employee_ids: mandateEmpIds.length ? mandateEmpIds : undefined,
      department_id: mandateDept || undefined,
      mandatory_cutoff: cutoff || undefined,
      note: mandateNote || undefined,
    }),
    onSuccess: (data) => {
      toast.success(`${Array.isArray(data) ? data.length : '?'} employees marked mandatory`)
      qc.invalidateQueries({ queryKey: ['schedule'] })
      setSelectedDay(null)
      setMandateEmpIds([])
      setMandateDept('')
      setMandateNote('')
    },
    onError: (e: any) => toast.error(e.response?.data?.detail ?? 'Failed'),
  })

  const dayMap = new Map(
    (weekData?.days ?? []).map((d: any) => [d.date, d])
  )

  const toggleEmp = (id: string) =>
    setMandateEmpIds(prev =>
      prev.includes(id) ? prev.filter(e => e !== id) : [...prev, id]
    )

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold">Schedule</h1>
          <p className="text-xs text-[var(--muted)] mt-0.5">Team schedule intents and mandatory attendance</p>
        </div>
        <div className="flex gap-2">
          <select value={deptFilter} onChange={e => setDeptFilter(e.target.value)} className="erp-select">
            <option value="">All Departments</option>
            {depts?.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-[1fr_340px] gap-6">
        {/* ── Week calendar ── */}
        <div className="card">
          {/* Week navigation */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--border)]">
            <button onClick={() => setWeekOf(w => subWeeks(w, 1))} className="btn btn-ghost btn-sm">
              <ChevronLeft size={14} />
            </button>
            <span className="font-display font-semibold text-sm">
              {format(weekOf, 'd MMM')} – {format(addDays(weekOf, 4), 'd MMM yyyy')}
            </span>
            <button onClick={() => setWeekOf(w => addWeeks(w, 1))} className="btn btn-ghost btn-sm">
              <ChevronRight size={14} />
            </button>
          </div>

          {isLoading ? <PageLoader /> : (
            <div className="grid grid-cols-5 divide-x divide-[var(--border)]">
              {weekDays.map(day => {
                const ds = format(day, 'yyyy-MM-dd')
                const dayData = dayMap.get(ds)
                const todayBool = isToday(day)
                const isSelected = selectedDay === ds

                return (
                  <div
                    key={ds}
                    onClick={() => setSelectedDay(isSelected ? null : ds)}
                    className={`p-4 cursor-pointer transition-colors min-h-[360px] flex flex-col
                      ${isSelected ? 'bg-[var(--accent-glow)]' : 'hover:bg-[var(--bg-3)]'}
                    `}
                  >
                    {/* Day header */}
                    <div className={`mb-3 pb-2 border-b ${todayBool ? 'border-[var(--accent)]' : 'border-[var(--border)]'}`}>
                      <p className={`text-[10px] font-mono uppercase tracking-wider ${todayBool ? 'text-[var(--accent)]' : 'text-[var(--muted)]'}`}>
                        {format(day, 'EEE')}
                      </p>
                      <p className={`font-display text-xl font-semibold ${todayBool ? 'text-[var(--accent)]' : 'text-[var(--text)]'}`}>
                        {format(day, 'd')}
                      </p>
                    </div>

                    {/* Count chips */}
                    {dayData && (
                      <div className="flex flex-col gap-1 mb-3">
                        {dayData.office_count > 0 && (
                          <div className="flex items-center gap-1.5 text-[10px] text-[var(--emerald)] bg-[rgba(45,212,160,0.08)] px-2 py-0.5 rounded">
                            <Building2 size={9} /> {dayData.office_count} office
                          </div>
                        )}
                        {dayData.wfh_count > 0 && (
                          <div className="flex items-center gap-1.5 text-[10px] text-[var(--sky)] bg-[rgba(91,164,232,0.08)] px-2 py-0.5 rounded">
                            <Home size={9} /> {dayData.wfh_count} WFH
                          </div>
                        )}
                        {dayData.leave_count > 0 && (
                          <div className="flex items-center gap-1.5 text-[10px] text-[var(--accent)] bg-[rgba(201,168,76,0.08)] px-2 py-0.5 rounded">
                            <Palmtree size={9} /> {dayData.leave_count} leave
                          </div>
                        )}
                        {dayData.mandatory_count > 0 && (
                          <div className="flex items-center gap-1.5 text-[10px] text-[var(--crimson)] bg-[rgba(224,92,107,0.08)] px-2 py-0.5 rounded">
                            <Lock size={9} /> {dayData.mandatory_count} mandatory
                          </div>
                        )}
                      </div>
                    )}

                    {/* Employee intent list */}
                    <div className="flex-1 space-y-1.5 overflow-y-auto">
                      {(dayData?.intents ?? []).map((intent: any) => {
                        const Icon = INTENT_ICONS[intent.intent_type] ?? Building2
                        return (
                          <div key={intent.id} className={`flex items-center gap-1.5 px-2 py-1 rounded text-[10px] ${INTENT_COLORS[intent.intent_type]}`}>
                            {intent.is_mandatory ? <Lock size={8} /> : <Icon size={8} />}
                            <span className="truncate">{intent.employee_name.split(' ')[0]}</span>
                          </div>
                        )
                      })}
                    </div>

                    {/* Tag mandatory CTA */}
                    {isSelected && (
                      <div className="mt-3 pt-2 border-t border-[var(--border)]">
                        <p className="text-[9px] font-mono text-[var(--accent)] uppercase tracking-wider">Selected → configure →</p>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* ── Mandatory tagging panel ── */}
        <div className="space-y-4">
          {selectedDay ? (
            <div className="card p-5 border-[rgba(224,92,107,0.3)] animate-slide-up">
              <div className="flex items-center gap-2 mb-4">
                <AlertTriangle size={15} className="text-[var(--crimson)]" />
                <h3 className="font-display font-semibold text-sm">Mandate Office Attendance</h3>
              </div>

              <div className="bg-[var(--bg-3)] border border-[var(--border)] rounded-lg px-3 py-2 mb-4">
                <p className="text-xs text-[var(--muted)]">For</p>
                <p className="font-mono text-sm text-[var(--accent)] font-medium">
                  {format(new Date(selectedDay + 'T00:00:00'), 'EEEE, d MMMM yyyy')}
                </p>
              </div>

              {/* Quick: entire department */}
              <div className="mb-4">
                <label className="erp-label">Tag entire department</label>
                <select
                  value={mandateDept}
                  onChange={e => { setMandateDept(e.target.value); setMandateEmpIds([]) }}
                  className="erp-select w-full"
                >
                  <option value="">— Or select individuals below —</option>
                  {depts?.map(d => <option key={d.id} value={d.id}>{d.name} ({d.employee_count})</option>)}
                </select>
              </div>

              {/* Or: individual employees */}
              {!mandateDept && (
                <div className="mb-4">
                  <label className="erp-label">Select employees</label>
                  <div className="max-h-40 overflow-y-auto space-y-1 border border-[var(--border)] rounded-lg p-2">
                    {(employees?.items ?? []).map((emp: any) => (
                      <div
                        key={emp.id}
                        onClick={() => toggleEmp(emp.id)}
                        className={`flex items-center gap-2.5 px-2 py-1.5 rounded cursor-pointer transition-colors ${
                          mandateEmpIds.includes(emp.id)
                            ? 'bg-[rgba(224,92,107,0.1)] border border-[rgba(224,92,107,0.2)]'
                            : 'hover:bg-[var(--bg-4)]'
                        }`}
                      >
                        <div className={`w-3.5 h-3.5 rounded border flex items-center justify-center flex-shrink-0 ${
                          mandateEmpIds.includes(emp.id)
                            ? 'bg-[var(--crimson)] border-[var(--crimson)]'
                            : 'border-[var(--border)]'
                        }`}>
                          {mandateEmpIds.includes(emp.id) && <Check size={9} className="text-white" />}
                        </div>
                        <Avatar name={emp.full_name} size="sm" />
                        <div className="min-w-0">
                          <p className="text-xs font-medium truncate">{emp.full_name}</p>
                          <p className="text-[10px] text-[var(--muted)] font-mono">{emp.department_name ?? '—'}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                  {mandateEmpIds.length > 0 && (
                    <p className="text-[10px] text-[var(--crimson)] mt-1">{mandateEmpIds.length} employee(s) selected</p>
                  )}
                </div>
              )}

              {/* Cutoff time */}
              <div className="mb-3">
                <label className="erp-label">Must arrive by</label>
                <input type="time" value={cutoff} onChange={e => setCutoff(e.target.value)} className="erp-input" />
                <p className="text-[10px] text-[var(--muted)] mt-1">No-show alert sent if not punched in by this time</p>
              </div>

              {/* Note */}
              <div className="mb-4">
                <label className="erp-label">Reason / note (shown to employees)</label>
                <input
                  type="text"
                  value={mandateNote}
                  onChange={e => setMandateNote(e.target.value)}
                  placeholder="e.g. Board meeting, Client visit…"
                  className="erp-input"
                />
              </div>

              <div className="flex gap-2">
                <button onClick={() => setSelectedDay(null)} className="btn btn-ghost flex-1">Cancel</button>
                <button
                  onClick={() => mandate()}
                  disabled={mandating || (!mandateEmpIds.length && !mandateDept)}
                  className="btn btn-danger flex-1"
                >
                  {mandating && <Spinner size={13} className="text-[var(--crimson)]" />}
                  <AlertTriangle size={13} /> Mandate
                </button>
              </div>
            </div>
          ) : (
            <div className="card p-5">
              <div className="flex items-center gap-2 mb-3">
                <Users size={15} className="text-[var(--muted)]" />
                <h3 className="font-display font-semibold text-sm text-[var(--muted)]">Mandatory Tagging</h3>
              </div>
              <p className="text-xs text-[var(--muted)] leading-relaxed">
                Click any day on the calendar to tag employees as mandatory office attendance.
                They'll see a lock icon on that day and receive a no-show alert if they don't punch in by the cutoff time.
              </p>
            </div>
          )}

          {/* This week's mandatory summary */}
          <div className="card p-5">
            <h3 className="text-[10px] font-mono uppercase tracking-widest text-[var(--muted)] mb-3">This week — mandatory</h3>
            {(weekData?.days ?? []).every((d: any) => d.mandatory_count === 0) ? (
              <p className="text-xs text-[var(--muted)]">No mandatory attendance set for this week</p>
            ) : (
              <div className="space-y-2">
                {(weekData?.days ?? [])
                  .filter((d: any) => d.mandatory_count > 0)
                  .map((d: any) => (
                    <div key={d.date} className="flex items-center justify-between">
                      <span className="text-xs font-mono text-[var(--text)]">
                        {format(new Date(d.date + 'T00:00:00'), 'EEE d MMM')}
                      </span>
                      <span className="flex items-center gap-1 text-[10px] text-[var(--crimson)]">
                        <Lock size={9} /> {d.mandatory_count} employees
                      </span>
                    </div>
                  ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
