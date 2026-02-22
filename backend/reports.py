# app/api/v1/endpoints/reports.py
# ─────────────────────────────────────────────────────────────
# Phase 4 — Reporting endpoints.
#
#   GET /reports/daily              — EOD snapshot for one date
#   GET /reports/monthly/{emp_id}   — Employee monthly calendar + stats
#   GET /reports/departments        — Department comparison for a month
#   GET /reports/trend              — 6-month trend line data
#   GET /reports/export/csv         — CSV file download
#
# All endpoints are admin/manager only EXCEPT:
#   /reports/monthly/{emp_id}  — employees can fetch their own
#   /reports/trend             — employees see their own trend
# ─────────────────────────────────────────────────────────────

import io
from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.core.dependencies import DbSession, CurrentUser, AdminUser
from app.models.employee import EmployeeRole
from app.schemas.reports import (
    DailyReportOut, DailyEmployeeRow,
    MonthlyEmployeeReport, MonthlyDayRow,
    DepartmentComparisonOut, DepartmentMonthStats,
    AttendanceTrendOut, MonthTrendPoint,
)
from app.services.reports_service import ReportsService

router = APIRouter(prefix="/reports", tags=["Reports"])


# ── Daily EOD report ───────────────────────────────────────────────────────────

@router.get("/daily", response_model=DailyReportOut)
async def daily_report(
    db: DbSession,
    _: AdminUser,
    report_date: date = Query(default_factory=date.today, alias="date"),
    department_id: Optional[UUID] = Query(default=None),
):
    """
    Full attendance snapshot for one date.
    Shows every active employee — present, absent, or otherwise.
    Defaults to today. Filter by department_id for dept managers.
    """
    svc = ReportsService(db)
    data = await svc.get_daily_report(report_date, department_id)

    return DailyReportOut(
        date=data["date"],
        total_employees=data["total_employees"],
        present=data["present"],
        absent=data["absent"],
        late=data["late"],
        wfh=data["wfh"],
        half_day=data["half_day"],
        attendance_pct=data["attendance_pct"],
        average_hours=data["average_hours"],
        rows=[DailyEmployeeRow(**r) for r in data["rows"]],
    )


# ── Per-employee monthly report ────────────────────────────────────────────────

@router.get("/monthly/{employee_id}", response_model=MonthlyEmployeeReport)
async def monthly_employee_report(
    employee_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    month: int = Query(default=None, ge=1, le=12),
    year:  int = Query(default=None, ge=2020, le=2100),
):
    """
    Day-by-day breakdown for one employee in a given month.
    Returns calendar rows + summary stats.
    Employees can only see their own. Admins can see anyone.
    """
    # Access control
    if current_user.role == EmployeeRole.EMPLOYEE and current_user.id != employee_id:
        raise HTTPException(status_code=403, detail="Access denied")

    today = date.today()
    target_month = month or today.month
    target_year  = year  or today.year

    svc = ReportsService(db)
    data = await svc.get_monthly_employee_report(employee_id, target_year, target_month)

    if not data:
        raise HTTPException(status_code=404, detail="Employee not found")

    return MonthlyEmployeeReport(
        employee_id=data["employee_id"],
        employee_code=data["employee_code"],
        employee_name=data["employee_name"],
        department_name=data["department_name"],
        month=data["month"],
        year=data["year"],
        total_working_days=data["total_working_days"],
        days_present=data["days_present"],
        days_absent=data["days_absent"],
        days_late=data["days_late"],
        days_wfh=data["days_wfh"],
        days_half_day=data["days_half_day"],
        total_hours=data["total_hours"],
        average_hours=data["average_hours"],
        attendance_pct=data["attendance_pct"],
        days=[MonthlyDayRow(**d) for d in data["days"]],
    )


# ── Department comparison ──────────────────────────────────────────────────────

@router.get("/departments", response_model=DepartmentComparisonOut)
async def department_comparison(
    db: DbSession,
    _: AdminUser,
    month: int = Query(default=None, ge=1, le=12),
    year:  int = Query(default=None, ge=2020, le=2100),
):
    """Department-by-department stats for a given month."""
    today = date.today()
    svc = ReportsService(db)
    data = await svc.get_department_comparison(
        year  or today.year,
        month or today.month,
    )
    return DepartmentComparisonOut(
        month=data["month"],
        year=data["year"],
        departments=[DepartmentMonthStats(**d) for d in data["departments"]],
    )


# ── 6-month trend ──────────────────────────────────────────────────────────────

@router.get("/trend", response_model=AttendanceTrendOut)
async def attendance_trend(
    db: DbSession,
    current_user: CurrentUser,
    employee_id: Optional[UUID] = Query(default=None),
    months: int = Query(default=6, ge=3, le=24),
):
    """
    Attendance percentage trend for the last N months.
    - No employee_id → company-wide (admin only)
    - employee_id provided → that employee's trend
    - Employees automatically see their own data regardless of param
    """
    if current_user.role == EmployeeRole.EMPLOYEE:
        target_id = current_user.id
    else:
        target_id = employee_id  # None = company-wide

    svc = ReportsService(db)
    data = await svc.get_attendance_trend(months, target_id)

    return AttendanceTrendOut(
        employee_id=data["employee_id"],
        points=[MonthTrendPoint(**p) for p in data["points"]],
    )


# ── CSV export ─────────────────────────────────────────────────────────────────

@router.get("/export/csv")
async def export_csv(
    db: DbSession,
    actor: AdminUser,
    date_from: date = Query(...),
    date_to: date   = Query(...),
    employee_id: Optional[UUID] = Query(default=None),
    department_id: Optional[UUID] = Query(default=None),
):
    """
    Download attendance records as a CSV file.
    Streams the response so large exports don't time out.
    Admin/manager only — managers are restricted to their own dept.
    """
    from app.models.employee import EmployeeRole
    # Managers can only export their own department
    if actor.role == EmployeeRole.MANAGER:
        department_id = actor.department_id

    if date_to < date_from:
        raise HTTPException(status_code=400, detail="date_to must be after date_from")

    svc = ReportsService(db)
    csv_content = await svc.build_csv(date_from, date_to, employee_id, department_id)

    filename = f"attendance_{date_from}_{date_to}.csv"
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
