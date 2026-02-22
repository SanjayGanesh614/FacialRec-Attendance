// src/pages/admin/Departments.tsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Building2, Clock, Users } from 'lucide-react'
import toast from 'react-hot-toast'
import { departmentsApi } from '@/api'
import { SectionHeader, Modal, Field, Spinner, EmptyState, PageLoader } from '@/components/ui'

export const DepartmentsPage = () => {
  const qc = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const { data: depts, isLoading } = useQuery({ queryKey: ['departments'], queryFn: departmentsApi.list })

  const { mutate: create, isPending } = useMutation({
    mutationFn: (d: any) => departmentsApi.create(d),
    onSuccess: () => { toast.success('Department created'); qc.invalidateQueries({ queryKey: ['departments'] }); setShowCreate(false) },
    onError: (e: any) => toast.error(e.response?.data?.detail ?? 'Failed'),
  })

  const [form, setForm] = useState({ name: '', code: '', shift_start: '09:00', shift_end: '18:00', late_grace_minutes: 15, min_office_days_per_week: 0 })

  if (isLoading) return <PageLoader />

  return (
    <div className="space-y-6">
      <SectionHeader title="Departments" sub={`${depts?.length ?? 0} departments configured`}>
        <button onClick={() => setShowCreate(true)} className="btn btn-primary"><Plus size={14} /> Add Department</button>
      </SectionHeader>

      {depts?.length === 0 ? <EmptyState message="No departments yet. Create one to assign employees." /> : (
        <div className="grid grid-cols-2 gap-4">
          {depts?.map(dept => (
            <div key={dept.id} className="card p-5 hover:border-[var(--border-l)] transition-colors">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-[var(--bg-4)] border border-[var(--border)] flex items-center justify-center">
                    <Building2 size={15} className="text-[var(--accent)]" />
                  </div>
                  <div>
                    <p className="font-semibold text-sm">{dept.name}</p>
                    <p className="text-[10px] font-mono text-[var(--muted)] mt-0.5">{dept.code}</p>
                  </div>
                </div>
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded ${dept.is_active ? 'text-[var(--emerald)] bg-[rgba(45,212,160,0.08)]' : 'text-[var(--muted)] bg-[var(--bg-4)]'}`}>
                  {dept.is_active ? 'ACTIVE' : 'INACTIVE'}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-3 text-xs text-[var(--muted)]">
                <div className="flex items-center gap-1.5">
                  <Users size={12} />
                  <span>{dept.employee_count} employees</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Clock size={12} />
                  <span className="font-mono">{dept.shift_start} – {dept.shift_end}</span>
                </div>
                <div>Grace: <span className="font-mono text-[var(--text)]">{dept.late_grace_minutes}m</span></div>
                <div>Min office days: <span className="font-mono text-[var(--text)]">{dept.min_office_days_per_week}/wk</span></div>
              </div>
            </div>
          ))}
        </div>
      )}

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="New Department">
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <Field label="Department Name">
              <input className="erp-input" placeholder="Engineering" value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} />
            </Field>
            <Field label="Code (uppercase)">
              <input className="erp-input" placeholder="ENG" value={form.code}
                onChange={e => setForm(p => ({ ...p, code: e.target.value.toUpperCase() }))} />
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Shift Start"><input type="time" className="erp-input" value={form.shift_start} onChange={e => setForm(p => ({ ...p, shift_start: e.target.value }))} /></Field>
            <Field label="Shift End"><input type="time" className="erp-input" value={form.shift_end} onChange={e => setForm(p => ({ ...p, shift_end: e.target.value }))} /></Field>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Late Grace (mins)">
              <input type="number" className="erp-input" value={form.late_grace_minutes} onChange={e => setForm(p => ({ ...p, late_grace_minutes: Number(e.target.value) }))} />
            </Field>
            <Field label="Min Office Days/Week">
              <input type="number" min="0" max="7" className="erp-input" value={form.min_office_days_per_week} onChange={e => setForm(p => ({ ...p, min_office_days_per_week: Number(e.target.value) }))} />
            </Field>
          </div>
          <div className="flex gap-2 justify-end pt-2 border-t border-[var(--border)]">
            <button onClick={() => setShowCreate(false)} className="btn btn-ghost">Cancel</button>
            <button onClick={() => create(form)} disabled={isPending || !form.name || !form.code} className="btn btn-primary">
              {isPending && <Spinner size={13} className="text-[#0e0e12]" />} Create
            </button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
