// src/types/index.ts
// All types mirror the backend Pydantic schemas exactly.

export type Role = 'super_admin' | 'manager' | 'employee'

export type DailyStatus = 'present' | 'absent' | 'late' | 'half_day' | 'wfh' | 'leave' | 'holiday'

export type PunchAction = 'punch_in' | 'punch_out'

// ── Auth ──────────────────────────────────────────────────────────────────────

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface MeResponse {
  id: string
  employee_code: string
  full_name: string
  email: string
  role: Role
  department_name: string | null
  is_enrolled: boolean
}

// ── Department ─────────────────────────────────────────────────────────────────

export interface Department {
  id: string
  name: string
  code: string
  manager_id: string | null
  shift_start: string
  shift_end: string
  late_grace_minutes: number
  min_office_days_per_week: number
  is_active: boolean
  employee_count: number
}

export interface DepartmentCreate {
  name: string
  code: string
  shift_start?: string
  shift_end?: string
  late_grace_minutes?: number
  min_office_days_per_week?: number
}

// ── Employee ───────────────────────────────────────────────────────────────────

export interface Employee {
  id: string
  employee_code: string
  full_name: string
  email: string
  phone: string | null
  role: Role
  department: { id: string; name: string; code: string } | null
  joining_date: string | null
  designation: string | null
  is_enrolled: boolean
  enrollment_pending: boolean
  enrollment_notes: string | null
  is_active: boolean
  created_at: string
}

export interface EmployeeListItem {
  id: string
  employee_code: string
  full_name: string
  email: string
  role: Role
  department_name: string | null
  is_enrolled: boolean
  is_active: boolean
}

export interface PaginatedEmployees {
  total: number
  page: number
  page_size: number
  items: EmployeeListItem[]
}

export interface EmployeeCreate {
  full_name: string
  email: string
  password: string
  role: Role
  department_id?: string
  phone?: string
  joining_date?: string
  designation?: string
  employee_code?: string
}

// ── Attendance ─────────────────────────────────────────────────────────────────

export interface DailyAttendanceOut {
  id: string
  employee_id: string
  employee_name: string
  date: string
  punch_in: string | null
  punch_out: string | null
  hours_worked: number
  late_by_minutes: number
  status: DailyStatus
  is_late: boolean
  is_corrected: boolean
  correction_note: string | null
}

export interface PaginatedAttendance {
  total: number
  page: number
  page_size: number
  items: DailyAttendanceOut[]
}

// ── Schedule ───────────────────────────────────────────────────────────────────

export type IntentType = 'office' | 'wfh' | 'leave'

export interface ScheduleIntentOut {
  id: string
  employee_id: string
  employee_name: string
  employee_code: string
  date: string
  intent_type: IntentType
  note: string | null
  is_mandatory: boolean
  mandatory_cutoff: string | null
  alert_sent: boolean
  created_at: string
}

export interface DayScheduleOut {
  date: string
  intents: ScheduleIntentOut[]
  office_count: number
  wfh_count: number
  leave_count: number
  mandatory_count: number
}

export interface WeekSummaryOut {
  week_start: string
  days: DayScheduleOut[]
}

export interface EmployeeCalendarOut {
  employee_id: string
  employee_name: string
  intents: ScheduleIntentOut[]
}

export interface AttendanceSummary {
  total_working_days: number
  days_present: number
  days_absent: number
  days_late: number
  days_wfh: number
  attendance_percentage: number
  average_hours_per_day: number
}
