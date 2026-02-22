// src/pages/admin/Attendance.tsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Filter, Download, Edit2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { attendanceApi, departmentsApi } from '@/api'
import { SectionHeader, PageLoader, EmptyState, Pagination, Modal, Field, Spinner } from '@/components/ui'
import { statusBadgeClass, statusLabel, formatTime, formatHours, formatDate } from '@/utils'

export const AttendancePage = () => {
  const qc = useQueryClient()
  const [page, setPage] = useState(1)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo]     = useState('')
  const [deptId, setDeptId]     = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [correctionTarget, setCorrectionTarget] = useState<any>(null)

  const { data: depts } = useQuery({ queryKey: ['departments'], queryFn: departmentsApi.list })

  const { data, isLoading } = useQuery({
    queryKey: ['attendance', page, dateFrom, dateTo, deptId, statusFilter],
    queryFn: () => attendanceApi.list({
      page, page_size: 30,
      date_from: dateFrom || undefined,
      date_to:   dateTo   || undefined,
      department_id: deptId || undefined,
      status: statusFilter || undefined,
    }),
    placeholderData: (prev) => prev,
  })

  const { mutate: correct, isPending: correcting } = useMutation({
    mutationFn: (payload: any) => attendanceApi.correct(payload),
    onSuccess: () => {
      toast.success('Attendance corrected')
      setCorrectionTarget(null)
      qc.invalidateQueries({ queryKey: ['attendance'] })
    },
    onError: () => toast.error('Correction failed'),
  })

  const exportCsv = () => {
    const rows = data?.items ?? []
    const csv = [
      'Date,Employee,Punch In,Punch Out,Hours,Status,Late By (mins)',
      ...rows.map(r =>
        `${r.date},${r.employee_name},${r.punch_in ?? ''},${r.punch_out ?? ''},${r.hours_worked},${r.status},${r.late_by_minutes}`
      )
    ].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob)
    a.download = `attendance-${dateFrom || 'all'}.csv`; a.click()
  }

  return (
    <div className="space-y-6">
      <SectionHeader title="Attendance Records" sub="Full attendance history with filtering">
        <button onClick={exportCsv} className="btn btn-ghost btn-sm">
          <Download size={13} /> Export CSV
        </button>
      </SectionHeader>

      {/* Filters */}
      <div className="card p-4">
        <div className="flex items-center gap-2 mb-3">
          <Filter size={13} className="text-[var(--muted)]" />
          <span className="text-[10px] font-mono uppercase tracking-widest text-[var(--muted)]">Filters</span>
        </div>
        <div className="grid grid-cols-4 gap-3">
          <div>
            <label className="erp-label">From</label>
            <input type="date" value={dateFrom} onChange={e => { setDateFrom(e.target.value); setPage(1) }} className="erp-input" />
          </div>
          <div>
            <label className="erp-label">To</label>
            <input type="date" value={dateTo} onChange={e => { setDateTo(e.target.value); setPage(1) }} className="erp-input" />
          </div>
          <div>
            <label className="erp-label">Department</label>
            <select value={deptId} onChange={e => { setDeptId(e.target.value); setPage(1) }} className="erp-select w-full">
              <option value="">All Departments</option>
              {depts?.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
          </div>
          <div>
            <label className="erp-label">Status</label>
            <select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1) }} className="erp-select w-full">
              <option value="">All Statuses</option>
              {['present','absent','late','wfh','half_day'].map(s =>
                <option key={s} value={s}>{statusLabel(s as any)}</option>
              )}
            </select>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="card">
        {isLoading ? <PageLoader /> : data?.items.length === 0 ? (
          <EmptyState message="No records match your filters" />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="erp-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Employee</th>
                    <th>Punch In</th>
                    <th>Punch Out</th>
                    <th>Hours</th>
                    <th>Late By</th>
                    <th>Status</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {data?.items.map(record => (
                    <tr key={record.id}>
                      <td className="font-mono text-xs">{formatDate(record.date)}</td>
                      <td className="font-medium">{record.employee_name}</td>
                      <td className="font-mono text-xs">{formatTime(record.punch_in)}</td>
                      <td className="font-mono text-xs">{formatTime(record.punch_out)}</td>
                      <td className="font-mono text-xs">{formatHours(record.hours_worked)}</td>
                      <td className="font-mono text-xs text-[var(--muted)]">
                        {record.late_by_minutes > 0 ? `${record.late_by_minutes}m` : '—'}
                      </td>
                      <td><span className={statusBadgeClass(record.status)}>{statusLabel(record.status)}</span></td>
                      <td>
                        <button
                          onClick={() => setCorrectionTarget(record)}
                          className="btn btn-ghost btn-sm opacity-0 group-hover:opacity-100"
                          title="Correct record"
                        >
                          <Edit2 size={12} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="px-5 pb-4">
              <Pagination page={page} total={data?.total ?? 0} pageSize={30} onChange={setPage} />
            </div>
          </>
        )}
      </div>

      {/* Correction Modal */}
      <CorrectionModal
        record={correctionTarget}
        onClose={() => setCorrectionTarget(null)}
        onSubmit={correct}
        loading={correcting}
      />
    </div>
  )
}

const CorrectionModal = ({ record, onClose, onSubmit, loading }: any) => {
  const [punchIn, setPunchIn]   = useState('')
  const [punchOut, setPunchOut] = useState('')
  const [reason, setReason]     = useState('')

  if (!record) return null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!reason) return toast.error('Reason is required')
    onSubmit({
      employee_id: record.employee_id,
      date: record.date,
      punch_in:  punchIn  || undefined,
      punch_out: punchOut || undefined,
      reason,
    })
  }

  return (
    <Modal open={!!record} onClose={onClose} title="Correct Attendance Record">
      <div className="mb-4 p-3 bg-[var(--bg-3)] rounded-lg border border-[var(--border)]">
        <p className="text-sm font-medium">{record.employee_name}</p>
        <p className="text-xs text-[var(--muted)] font-mono mt-0.5">{formatDate(record.date)}</p>
      </div>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <Field label="Corrected Punch In">
            <input type="time" value={punchIn} onChange={e => setPunchIn(e.target.value)} className="erp-input" />
          </Field>
          <Field label="Corrected Punch Out">
            <input type="time" value={punchOut} onChange={e => setPunchOut(e.target.value)} className="erp-input" />
          </Field>
        </div>
        <Field label="Reason (required)">
          <textarea
            value={reason}
            onChange={e => setReason(e.target.value)}
            placeholder="e.g. Recognition failed due to lighting — confirmed by ID card"
            className="erp-input resize-none h-20"
            required
          />
        </Field>
        <div className="flex gap-2 justify-end pt-2">
          <button type="button" onClick={onClose} className="btn btn-ghost">Cancel</button>
          <button type="submit" disabled={loading} className="btn btn-primary">
            {loading && <Spinner size={13} className="text-[#0e0e12]" />}
            Save Correction
          </button>
        </div>
      </form>
    </Modal>
  )
}
