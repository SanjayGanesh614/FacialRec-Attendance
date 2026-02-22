# app/schemas/reports.py
# ─────────────────────────────────────────────────────────────
# Pydantic response shapes for the /reports/* endpoints.
# Separate from attendance.py schemas — reports are aggregated
# read-only views, not raw record shapes.
# ─────────────────────────────────────────────────────────────

from uuid import UUID
from datetime import date, time
from pydantic import BaseModel
from app.models.attendance import DailyStatus


# ── Daily EOD report ───────────────────────────────────────────────────────────

class DailyEmployeeRow(BaseModel):
    """One employee's row in the daily EOD report table."""
    employee_id:   UUID
    employee_code: str
    employee_name: str
    department_name: str | None
    punch_in:      time | None
    punch_out:     time | None
    hours_worked:  float
    late_by_minutes: int
    status:        DailyStatus
    is_late:       bool
    is_corrected:  bool


class DailyReportOut(BaseModel):
    """Full EOD report for one date."""
    date:           date
    total_employees: int
    present:        int
    absent:         int
    late:           int
    wfh:            int
    half_day:       int
    attendance_pct: float
    average_hours:  float
    rows:           list[DailyEmployeeRow]


# ── Per-employee monthly report ────────────────────────────────────────────────

class MonthlyDayRow(BaseModel):
    """One day in an employee's monthly calendar — used to build heatmap/chart."""
    date:          date
    status:        DailyStatus
    punch_in:      time | None
    punch_out:     time | None
    hours_worked:  float
    late_by_minutes: int
    is_corrected:  bool


class MonthlyEmployeeReport(BaseModel):
    """Full monthly report for one employee — calendar rows + summary stats."""
    employee_id:    UUID
    employee_code:  str
    employee_name:  str
    department_name: str | None
    month:          int
    year:           int
    # Summary stats
    total_working_days: int
    days_present:   int
    days_absent:    int
    days_late:      int
    days_wfh:       int
    days_half_day:  int
    total_hours:    float
    average_hours:  float
    attendance_pct: float
    # Day-by-day rows (for calendar / heatmap rendering)
    days:           list[MonthlyDayRow]


# ── Department comparison ──────────────────────────────────────────────────────

class DepartmentMonthStats(BaseModel):
    """One department's stats for a month — used by the comparison bar chart."""
    department_id:   UUID
    department_name: str
    department_code: str
    employee_count:  int
    days_present:    int
    days_absent:     int
    days_late:       int
    attendance_pct:  float
    average_hours:   float


class DepartmentComparisonOut(BaseModel):
    month:       int
    year:        int
    departments: list[DepartmentMonthStats]


# ── Trend data (for the 6-month line chart) ───────────────────────────────────

class MonthTrendPoint(BaseModel):
    month:          int
    year:           int
    label:          str          # "Jan 2025"
    attendance_pct: float
    days_present:   int
    days_absent:    int
    days_late:      int


class AttendanceTrendOut(BaseModel):
    """6-month trend — used by both admin overview and employee personal chart."""
    employee_id:  UUID | None   # None = company-wide
    points:       list[MonthTrendPoint]
