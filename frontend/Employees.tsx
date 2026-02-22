// src/pages/admin/Employees.tsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Search, Fingerprint, CheckCircle2, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import { employeesApi, departmentsApi } from '@/api'
import { SectionHeader, PageLoader, EmptyState, Pagination, Avatar, Modal, Field, Spinner } from '@/components/ui'
import { roleLabel } from '@/utils'
import type { EmployeeCreate } from '@/types'

export const EmployeesPage = () => {
  const qc = useQueryClient()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [deptFilter, setDeptFilter] = useState('')
  const [showCreate, setShowCreate] = useState(false)

  const { data: depts } = useQuery({ queryKey: ['departments'], queryFn: departmentsApi.list })

  const { data, isLoading } = useQuery({
    queryKey: ['employees', page, search, deptFilter],
    queryFn: () => employeesApi.list({
      page, page_size: 25,
      search: search || undefined,
      department_id: deptFilter || undefined,
    }),
    placeholderData: p => p,
  })

  const { mutate: triggerEnroll } = useMutation({
    mutationFn: (id: string) => employeesApi.triggerEnrollment(id),
    onSuccess: (_, id) => {
      toast.success('Enrollment queued — approach the Pi terminal')
      qc.invalidateQueries({ queryKey: ['employees'] })
    },
    onError: () => toast.error('Failed to trigger enrollment'),
  })

  return (
    <div className="space-y-6">
      <SectionHeader title="Employees" sub={`${data?.total ?? 0} active employees`}>
        <button onClick={() => setShowCreate(true)} className="btn btn-primary">
          <Plus size={14} /> Add Employee
        </button>
      </SectionHeader>

      {/* Search & filter */}
      <div className="flex gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" />
          <input
            type="text"
            placeholder="Search name, email, code…"
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1) }}
            className="erp-input pl-9"
          />
        </div>
        <select value={deptFilter} onChange={e => { setDeptFilter(e.target.value); setPage(1) }} className="erp-select">
          <option value="">All Departments</option>
          {depts?.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
      </div>

      {/* Table */}
      <div className="card">
        {isLoading ? <PageLoader /> : data?.items.length === 0 ? (
          <EmptyState message="No employees found" />
        ) : (
          <>
            <table className="erp-table">
              <thead>
                <tr>
                  <th>Employee</th>
                  <th>Code</th>
                  <th>Department</th>
                  <th>Role</th>
                  <th>Face Enrolled</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {data?.items.map(emp => (
                  <tr key={emp.id} className="group">
                    <td>
                      <div className="flex items-center gap-3">
                        <Avatar name={emp.full_name} size="sm" />
                        <div>
                          <p className="font-medium text-sm">{emp.full_name}</p>
                          <p className="text-xs text-[var(--muted)]">{emp.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="font-mono text-xs text-[var(--muted)]">{emp.employee_code}</td>
                    <td className="text-sm">{emp.department_name ?? <span className="text-[var(--dim)]">—</span>}</td>
                    <td>
                      <span className="text-xs text-[var(--muted)]">{roleLabel(emp.role)}</span>
                    </td>
                    <td>
                      {emp.is_enrolled ? (
                        <span className="flex items-center gap-1.5 text-xs text-[var(--emerald)]">
                          <CheckCircle2 size={13} /> Enrolled
                        </span>
                      ) : (
                        <span className="flex items-center gap-1.5 text-xs text-[var(--crimson)]">
                          <AlertCircle size={13} /> Not enrolled
                        </span>
                      )}
                    </td>
                    <td>
                      <button
                        onClick={() => triggerEnroll(emp.id)}
                        className="btn btn-ghost btn-sm"
                        title="Trigger face enrollment"
                      >
                        <Fingerprint size={12} />
                        {emp.is_enrolled ? 'Re-enroll' : 'Enroll'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="px-5 pb-4">
              <Pagination page={page} total={data?.total ?? 0} pageSize={25} onChange={setPage} />
            </div>
          </>
        )}
      </div>

      <CreateEmployeeModal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        departments={depts ?? []}
        onCreated={() => qc.invalidateQueries({ queryKey: ['employees'] })}
      />
    </div>
  )
}

const CreateEmployeeModal = ({ open, onClose, departments, onCreated }: any) => {
  const qc = useQueryClient()
  const [form, setForm] = useState<EmployeeCreate>({
    full_name: '', email: '', password: '', role: 'employee',
    department_id: undefined, phone: undefined, designation: undefined,
  })

  const { mutate: create, isPending } = useMutation({
    mutationFn: () => employeesApi.create(form),
    onSuccess: (emp) => {
      toast.success(`${emp.full_name} added — don't forget to enroll their face`)
      onCreated()
      onClose()
      setForm({ full_name: '', email: '', password: '', role: 'employee' })
    },
    onError: (e: any) => toast.error(e.response?.data?.detail ?? 'Failed to create employee'),
  })

  const f = (k: keyof EmployeeCreate) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm(prev => ({ ...prev, [k]: e.target.value || undefined }))

  return (
    <Modal open={open} onClose={onClose} title="Add New Employee" width="max-w-xl">
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <Field label="Full Name">
            <input className="erp-input" placeholder="Alice Smith" value={form.full_name}
              onChange={e => setForm(p => ({ ...p, full_name: e.target.value }))} />
          </Field>
          <Field label="Email">
            <input className="erp-input" type="email" placeholder="alice@company.com" value={form.email}
              onChange={e => setForm(p => ({ ...p, email: e.target.value }))} />
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Password">
            <input className="erp-input" type="password" placeholder="min 8 characters" value={form.password}
              onChange={e => setForm(p => ({ ...p, password: e.target.value }))} />
          </Field>
          <Field label="Phone (optional)">
            <input className="erp-input" placeholder="+91 9876543210" value={form.phone ?? ''}
              onChange={f('phone')} />
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Department">
            <select className="erp-select w-full" value={form.department_id ?? ''}
              onChange={e => setForm(p => ({ ...p, department_id: e.target.value || undefined }))}>
              <option value="">No department</option>
              {departments.map((d: any) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
          </Field>
          <Field label="Role">
            <select className="erp-select w-full" value={form.role}
              onChange={e => setForm(p => ({ ...p, role: e.target.value as any }))}>
              <option value="employee">Employee</option>
              <option value="manager">Manager</option>
              <option value="super_admin">Super Admin</option>
            </select>
          </Field>
        </div>
        <Field label="Designation (optional)">
          <input className="erp-input" placeholder="Senior Engineer" value={form.designation ?? ''}
            onChange={f('designation')} />
        </Field>

        <div className="flex gap-2 justify-end pt-2 border-t border-[var(--border)]">
          <button type="button" onClick={onClose} className="btn btn-ghost">Cancel</button>
          <button
            onClick={() => create()}
            disabled={isPending || !form.full_name || !form.email || !form.password}
            className="btn btn-primary"
          >
            {isPending && <Spinner size={13} className="text-[#0e0e12]" />}
            Create Employee
          </button>
        </div>
      </div>
    </Modal>
  )
}
