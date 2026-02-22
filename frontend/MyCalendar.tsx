// src/pages/employee/MyCalendar.tsx
// ─────────────────────────────────────────────────────────────
// Employee's personal schedule calendar.
// Shows attendance history overlaid with schedule intents.
// Employee can click any future/today date to set their intent:
//   🏢 Office  🏠 WFH  🌴 Leave
// Admin-mandatory days show a lock icon and cannot be changed.
// ─────────────────────────────────────────────────────────────

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Building2, Home, Palmtree, Lock, X, ChevronLeft, ChevronRight } from 'lucide-react'
import toast from 'react-hot-toast'
import { scheduleApi, attendanceApi } from '@/api'
import { PageLoader, Spinner } from '@/components/ui'
import { statusBadgeClass, statusLabel } from '@/utils'
import { format, startOfMonth, endOfMonth, startOfWeek, endOfWeek, eachDayOfInterval, isSameMonth, isToday, isBefore, parseISO, addMonths, subMonths } from 'date-fns'

const INTENT_STYLES = {
  office: { label: 'Office', color: 'bg-[rgba(45,212,160,0.15)] border-[rgba(45,212,160,0.35)] text-[var(--emerald)]',  icon: Building2 },
  wfh:    { label: 'WFH',    color: 'bg-[rgba(91,164,232,0.15)] border-[rgba(91,164,232,0.35)] text-[var(--sky)]',     icon: Home },
  leave:  { label: 'Leave',  color: 'bg-[rgba(201,168,76,0.12)] border-[rgba(201,168,76,0.3)] text-[var(--accent)]',   icon: Palmtree },
}

export const MyCalendar = () => {
  const qc = useQueryClient()
  const [currentMonth, setCurrentMonth] = useState(new Date())
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [intentNote, setIntentNote] = useState('')

  const monthStart = startOfMonth(currentMonth)
  const monthEnd   = endOfMonth(currentMonth)
  const calStart   = startOfWeek(monthStart, { weekStartsOn: 1 }) // Monday
  const calEnd     = endOfWeek(monthEnd, { weekStartsOn: 1 })
  const allDays    = eachDayOfInterval({ start: calStart, end: calEnd })

  const dateFrom = format(monthStart, 'yyyy-MM-dd')
  const dateTo   = format(monthEnd,   'yyyy-MM-dd')

  // Fetch both schedule intents and attendance records for the month
  const { data: scheduleData, isLoading: loadingSched } = useQuery({
    queryKey: ['my-schedule', dateFrom, dateTo],
    queryFn: () => scheduleApi.mySchedule(dateFrom, dateTo),
  })

  const { data: attData } = useQuery({
    queryKey: ['my-attendance', 'calendar', dateFrom, dateTo],
    queryFn: () => attendanceApi.mine({ page: 1, page_size: 31, date_from: dateFrom, date_to: dateTo }),
  })

  // Build lookup maps
  const intentMap = new Map(
    (scheduleData?.intents ?? []).map((i: any) => [i.date, i])
  )
  const attMap = new Map(
    (attData?.items ?? []).map((r: any) => [r.date, r])
  )

  const { mutate: setIntent, isPending: settingIntent } = useMutation({
    mutationFn: (type: string) => scheduleApi.setIntent({
      date: selectedDate!,
      intent_type: type,
      note: intentNote || undefined,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['my-schedule'] })
      setSelectedDate(null)
      setIntentNote('')
      toast.success('Schedule updated')
    },
    onError: (e: any) => toast.error(e.response?.data?.detail ?? 'Could not update'),
  })

  const { mutate: clearIntent } = useMutation({
    mutationFn: (date: string) => scheduleApi.clearIntent(date),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['my-schedule'] })
      toast.success('Intent cleared')
    },
  })

  const today = new Date()
  const isPast = (d: Date) => isBefore(d, today) && !isToday(d)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold">My Calendar</h1>
          <p className="text-xs text-[var(--muted)] mt-0.5">Plan your work schedule — office, WFH, or leave</p>
        </div>
        {/* Legend */}
        <div className="flex items-center gap-4">
          {Object.entries(INTENT_STYLES).map(([k, s]) => (
            <div key={k} className="flex items-center gap-1.5">
              <div className={`w-2.5 h-2.5 rounded-sm border ${s.color}`} />
              <span className="text-[10px] text-[var(--muted)]">{s.label}</span>
            </div>
          ))}
          <div className="flex items-center gap-1.5">
            <Lock size={10} className="text-[var(--accent)]" />
            <span className="text-[10px] text-[var(--muted)]">Mandatory</span>
          </div>
        </div>
      </div>

      <div className="card p-5">
        {/* Month navigation */}
        <div className="flex items-center justify-between mb-5">
          <button onClick={() => setCurrentMonth(m => subMonths(m, 1))} className="btn btn-ghost btn-sm">
            <ChevronLeft size={14} />
          </button>
          <h2 className="font-display text-lg font-semibold">
            {format(currentMonth, 'MMMM yyyy')}
          </h2>
          <button onClick={() => setCurrentMonth(m => addMonths(m, 1))} className="btn btn-ghost btn-sm">
            <ChevronRight size={14} />
          </button>
        </div>

        {/* Day headers */}
        <div className="grid grid-cols-7 mb-1">
          {['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].map(d => (
            <div key={d} className="text-center text-[10px] font-mono text-[var(--muted)] py-2 uppercase tracking-wider">{d}</div>
          ))}
        </div>

        {/* Calendar grid */}
        {loadingSched ? (
          <div className="flex justify-center py-20"><Spinner size={24} /></div>
        ) : (
          <div className="grid grid-cols-7 gap-1">
            {allDays.map((day) => {
              const ds = format(day, 'yyyy-MM-dd')
              const inMonth = isSameMonth(day, currentMonth)
              const isWeekend = day.getDay() === 0 || day.getDay() === 6
              const past = isPast(day)
              const today_ = isToday(day)
              const intent = intentMap.get(ds) as any
              const att    = attMap.get(ds) as any
              const isMandatory = intent?.is_mandatory
              const intentStyle = intent ? INTENT_STYLES[intent.intent_type as keyof typeof INTENT_STYLES] : null
              const isSelected = selectedDate === ds

              return (
                <div
                  key={ds}
                  onClick={() => {
                    if (!inMonth || past || isWeekend || isMandatory) return
                    setSelectedDate(isSelected ? null : ds)
                  }}
                  className={`
                    relative border rounded-lg p-2 min-h-[72px] transition-all
                    ${!inMonth ? 'opacity-25 border-transparent' : ''}
                    ${isWeekend && inMonth ? 'border-[var(--border)] bg-[var(--bg-3)] cursor-default' : ''}
                    ${inMonth && !isWeekend && !past && !isMandatory ? 'cursor-pointer hover:border-[var(--accent)] hover:bg-[var(--accent-glow)]' : ''}
                    ${past && inMonth ? 'opacity-60 cursor-default border-[var(--border)]' : ''}
                    ${intentStyle && inMonth ? `border ${intentStyle.color}` : inMonth && !isWeekend && !past ? 'border-[var(--border)]' : ''}
                    ${today_ ? 'ring-2 ring-[var(--accent)] ring-offset-1 ring-offset-[var(--bg)]' : ''}
                    ${isSelected ? 'ring-2 ring-[var(--accent)] bg-[var(--accent-glow)]' : ''}
                  `}
                >
                  {/* Day number */}
                  <div className="flex items-center justify-between mb-1">
                    <span className={`text-xs font-mono font-medium ${today_ ? 'text-[var(--accent)]' : inMonth ? 'text-[var(--text)]' : 'text-[var(--dim)]'}`}>
                      {format(day, 'd')}
                    </span>
                    {isMandatory && <Lock size={9} className="text-[var(--accent)]" />}
                  </div>

                  {/* Intent chip */}
                  {intentStyle && inMonth && (
                    <div className="flex items-center gap-1 mb-1">
                      <intentStyle.icon size={9} />
                      <span className="text-[9px] font-mono">{intentStyle.label}</span>
                    </div>
                  )}

                  {/* Attendance status (past days) */}
                  {att && inMonth && (
                    <div className={`text-[8px] font-mono mt-auto ${
                      att.status === 'present' ? 'text-[var(--emerald)]' :
                      att.status === 'late' ? 'text-[var(--accent)]' :
                      att.status === 'absent' ? 'text-[var(--crimson)]' : 'text-[var(--muted)]'
                    }`}>
                      {att.punch_in ? att.punch_in.slice(0,5) : att.status}
                    </div>
                  )}

                  {/* Clear button */}
                  {intent && !isMandatory && !past && inMonth && (
                    <button
                      onClick={(e) => { e.stopPropagation(); clearIntent(ds) }}
                      className="absolute top-1 right-1 text-[var(--muted)] hover:text-[var(--crimson)] transition-colors"
                    >
                      <X size={9} />
                    </button>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Intent picker panel */}
      {selectedDate && (
        <div className="card p-5 border-[var(--accent)] border-opacity-50 animate-slide-up">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-[10px] font-mono uppercase tracking-widest text-[var(--muted)]">Setting intent for</p>
              <p className="font-display text-base font-semibold mt-0.5">
                {format(parseISO(selectedDate), 'EEEE, d MMMM yyyy')}
              </p>
            </div>
            <button onClick={() => setSelectedDate(null)} className="text-[var(--muted)] hover:text-[var(--text)]">
              <X size={16} />
            </button>
          </div>

          <div className="flex gap-3 mb-4">
            {Object.entries(INTENT_STYLES).map(([type, style]) => {
              const Icon = style.icon
              const current = intentMap.get(selectedDate) as any
              const isActive = current?.intent_type === type
              return (
                <button
                  key={type}
                  onClick={() => setIntent(type)}
                  disabled={settingIntent}
                  className={`
                    flex-1 flex flex-col items-center gap-2 py-4 rounded-lg border transition-all
                    ${isActive
                      ? `${style.color} font-semibold`
                      : 'border-[var(--border)] text-[var(--muted)] hover:border-[var(--border-l)] hover:text-[var(--text)]'
                    }
                  `}
                >
                  {settingIntent ? <Spinner size={16} /> : <Icon size={18} />}
                  <span className="text-xs">{style.label}</span>
                </button>
              )
            })}
          </div>

          <div>
            <label className="erp-label">Add a note (optional)</label>
            <input
              type="text"
              value={intentNote}
              onChange={e => setIntentNote(e.target.value)}
              placeholder="e.g. Client meeting, doctor appointment…"
              className="erp-input"
            />
          </div>
        </div>
      )}

      {/* Monthly intent summary */}
      <div className="grid grid-cols-3 gap-4">
        {Object.entries(INTENT_STYLES).map(([type, style]) => {
          const Icon = style.icon
          const count = (scheduleData?.intents ?? []).filter((i: any) => i.intent_type === type).length
          return (
            <div key={type} className={`card p-4 border ${style.color}`}>
              <div className="flex items-center gap-3">
                <Icon size={16} />
                <div>
                  <p className="text-xs text-[var(--muted)]">{style.label} days planned</p>
                  <p className="font-display text-2xl font-semibold">{count}</p>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
