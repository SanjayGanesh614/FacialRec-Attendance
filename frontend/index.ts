// src/api/index.ts
// All API call functions — imported by React Query hooks.

import client from './client'
import type {
  TokenResponse, MeResponse,
  Department, DepartmentCreate,
  PaginatedEmployees, Employee, EmployeeCreate,
  PaginatedAttendance, DailyAttendanceOut, AttendanceSummary,
} from '@/types'

// ── Auth ──────────────────────────────────────────────────────────────────────

export const authApi = {
  login: (email: string, password: string) =>
    client.post<TokenResponse>('/auth/login', { email, password }).then(r => r.data),

  me: () =>
    client.get<MeResponse>('/auth/me').then(r => r.data),

  refresh: (refresh_token: string) =>
    client.post<{ access_token: string }>('/auth/refresh', { refresh_token }).then(r => r.data),
}

// ── Employees ─────────────────────────────────────────────────────────────────

export const employeesApi = {
  list: (params?: {
    page?: number; page_size?: number; search?: string;
    department_id?: string; is_active?: boolean
  }) => client.get<PaginatedEmployees>('/employees', { params }).then(r => r.data),

  get: (id: string) =>
    client.get<Employee>(`/employees/${id}`).then(r => r.data),

  create: (data: EmployeeCreate) =>
    client.post<Employee>('/employees', data).then(r => r.data),

  update: (id: string, data: Partial<EmployeeCreate>) =>
    client.patch<Employee>(`/employees/${id}`, data).then(r => r.data),

  triggerEnrollment: (id: string) =>
    client.post(`/employees/${id}/enroll`).then(r => r.data),

  changePassword: (id: string, current_password: string, new_password: string) =>
    client.post(`/employees/${id}/change-password`, { current_password, new_password }),
}

// ── Departments ────────────────────────────────────────────────────────────────

export const departmentsApi = {
  list: () =>
    client.get<Department[]>('/departments').then(r => r.data),

  get: (id: string) =>
    client.get<Department>(`/departments/${id}`).then(r => r.data),

  create: (data: DepartmentCreate) =>
    client.post<Department>('/departments', data).then(r => r.data),

  update: (id: string, data: Partial<DepartmentCreate & { manager_id: string; is_active: boolean }>) =>
    client.patch<Department>(`/departments/${id}`, data).then(r => r.data),
}

// ── Schedule ──────────────────────────────────────────────────────────────────

export const scheduleApi = {
  // Employee sets their own intent
  setIntent: (data: { date: string; intent_type: string; note?: string }) =>
    client.post('/schedule/intent', data).then(r => r.data),

  clearIntent: (for_date: string) =>
    client.delete('/schedule/intent', { params: { for_date } }),

  // Employee's own calendar
  mySchedule: (date_from: string, date_to: string) =>
    client.get('/schedule/me', { params: { date_from, date_to } }).then(r => r.data),

  // Admin: team views
  teamSchedule: (date_from: string, date_to: string, department_id?: string) =>
    client.get('/schedule/team', { params: { date_from, date_to, department_id } }).then(r => r.data),

  weekSummary: (week_start: string, department_id?: string) =>
    client.get('/schedule/week', { params: { week_start, department_id } }).then(r => r.data),

  // Admin: mandatory tagging
  mandate: (data: {
    date: string
    employee_ids?: string[]
    department_id?: string
    mandatory_cutoff?: string
    note?: string
  }) => client.post('/schedule/mandate', data).then(r => r.data),

  removeMandate: (data: { date: string; employee_ids: string[] }) =>
    client.delete('/schedule/mandate', { data }).then(r => r.data),
}

export const attendanceApi = {
  list: (params?: {
    page?: number; page_size?: number;
    date_from?: string; date_to?: string;
    employee_id?: string; department_id?: string; status?: string
  }) => client.get<PaginatedAttendance>('/attendance', { params }).then(r => r.data),

  today: () =>
    client.get<DailyAttendanceOut[]>('/attendance/today').then(r => r.data),

  mine: (params?: { page?: number; date_from?: string; date_to?: string }) =>
    client.get<PaginatedAttendance>('/attendance/me', { params }).then(r => r.data),

  summary: (params?: { employee_id?: string; month?: number; year?: number }) =>
    client.get<AttendanceSummary>('/attendance/summary', { params }).then(r => r.data),

  correct: (data: {
    employee_id: string; date: string;
    punch_in?: string; punch_out?: string;
    status?: string; reason: string
  }) => client.post('/attendance/correct', data).then(r => r.data),
}

// ── Reports ────────────────────────────────────────────────────────────────────

export const reportsApi = {
  daily: (date?: string, department_id?: string) =>
    client.get('/reports/daily', { params: { date, department_id } }).then(r => r.data),

  monthly: (employee_id: string, month?: number, year?: number) =>
    client.get(`/reports/monthly/${employee_id}`, { params: { month, year } }).then(r => r.data),

  departments: (month?: number, year?: number) =>
    client.get('/reports/departments', { params: { month, year } }).then(r => r.data),

  trend: (employee_id?: string, months = 6) =>
    client.get('/reports/trend', { params: { employee_id, months } }).then(r => r.data),

  exportCsv: (date_from: string, date_to: string, employee_id?: string, department_id?: string) => {
    const params = new URLSearchParams({ date_from, date_to })
    if (employee_id) params.append('employee_id', employee_id)
    if (department_id) params.append('department_id', department_id)
    // Trigger browser download
    window.open(`/api/v1/reports/export/csv?${params}`, '_blank')
  },
}
