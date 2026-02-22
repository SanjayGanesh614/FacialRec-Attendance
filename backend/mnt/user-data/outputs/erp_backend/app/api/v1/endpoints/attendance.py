# app/api/v1/endpoints/attendance.py
# ─────────────────────────────────────────────────────────────
# Attendance endpoints:
#   POST /attendance/punch      ← Pi calls this (device key auth)
#   GET  /attendance            ← Admin queries attendance records
#   GET  /attendance/today      ← Who is in the office right now
#   GET  /attendance/me         ← Employee sees own records
#   GET  /attendance/summary    ← Monthly summary stats
#   POST /attendance/correct    ← Admin manual correction
# ─────────────────────────────────────────────────────────────

from uuid import UUID
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Query, Request
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.core.dependencies import DbSession, CurrentUser, AdminUser, DeviceAuth
from app.models.employee import Employee, EmployeeRole
from app.models.attendance import DailyAttendance, DailyStatus, AttendanceEvent
from app.schemas.attendance import (
    PunchRequest, PunchResponse,
    DailyAttendanceOut, PaginatedAttendance,
    AttendanceSummary, AttendanceCorrection,
)
from app.services.attendance_service import AttendanceService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/attendance", tags=["Attendance"])


# ── Pi device punch endpoint ───────────────────────────────────────────────────

@router.post("/punch", response_model=PunchResponse)
async def handle_punch(
    body: PunchRequest,
    db: DbSession,
    _device: DeviceAuth,       # validates X-Api-Key header
):
    """
    Called by the Raspberry Pi when a face is recognised.
    Uses device API key auth (NOT JWT — Pi doesn't log in as a user).

    Looks up employee by employee_code, determines punch-in or punch-out,
    writes events, returns action so Pi knows what LED to flash.
    """
    # Find employee by code (what Pi sends as employee_id)
    result = await db.execute(
        select(Employee).where(
            Employee.employee_code == body.employee_id,
            Employee.is_active == True,   # noqa: E712
        )
    )
    employee = result.scalar_one_or_none()

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee '{body.employee_id}' not found or inactive",
        )

    # Process through business logic service
    svc = AttendanceService(db)
    action, daily = await svc.process_punch(
        employee=employee,
        device_id=body.device_id,
        event_time=body.timestamp,
    )

    return PunchResponse(
        success=True,
        action=action.value,
        employee_name=employee.full_name,
        message=f"{action.value.replace('_', ' ').title()} — {employee.full_name}",
    )


# ── Admin attendance queries ───────────────────────────────────────────────────

@router.get("", response_model=PaginatedAttendance)
async def list_attendance(
    db: DbSession,
    actor: AdminUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    employee_id: Optional[UUID] = Query(default=None),
    department_id: Optional[UUID] = Query(default=None),
    status_filter: Optional[DailyStatus] = Query(default=None, alias="status"),
):
    """
    Paginated attendance records with filtering.
    Managers see their department only.
    Super admins see everything.
    """
    from sqlalchemy import func

    query = select(DailyAttendance)

    # Managers are restricted to their own department
    if actor.role == EmployeeRole.MANAGER:
        query = query.join(Employee).where(
            Employee.department_id == actor.department_id
        )
    elif department_id:
        query = query.join(Employee).where(
            Employee.department_id == department_id
        )

    if employee_id:
        query = query.where(DailyAttendance.employee_id == employee_id)
    if date_from:
        query = query.where(DailyAttendance.date >= date_from)
    if date_to:
        query = query.where(DailyAttendance.date <= date_to)
    if status_filter:
        query = query.where(DailyAttendance.status == status_filter)

    # Count
    from sqlalchemy import func as sqlfunc
    count_result = await db.execute(
        select(sqlfunc.count()).select_from(query.subquery())
    )
    total = count_result.scalar_one()

    # Fetch page
    query = query.order_by(
        DailyAttendance.date.desc(), DailyAttendance.employee_id
    ).offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    records = result.scalars().all()

    items = [
        DailyAttendanceOut(
            id=r.id,
            employee_id=r.employee_id,
            employee_name=r.employee.full_name if r.employee else "—",
            date=r.date,
            punch_in=r.punch_in,
            punch_out=r.punch_out,
            hours_worked=r.hours_worked,
            late_by_minutes=r.late_by_minutes,
            status=r.status,
            is_late=r.is_late,
            is_corrected=r.is_corrected,
            correction_note=r.correction_note,
        )
        for r in records
    ]

    return PaginatedAttendance(total=total, page=page, page_size=page_size, items=items)


@router.get("/today", response_model=list[DailyAttendanceOut])
async def todays_attendance(db: DbSession, actor: AdminUser):
    """
    Everyone's attendance status for today.
    Used by admin dashboard for "who's in the office now" view.
    Returns all employees — including those with no punch yet (ABSENT).
    """
    today = date.today()

    # Get all active employees (with dept filter for managers)
    emp_query = select(Employee).where(Employee.is_active == True)  # noqa: E712
    if actor.role == EmployeeRole.MANAGER:
        emp_query = emp_query.where(Employee.department_id == actor.department_id)

    emp_result = await db.execute(emp_query)
    employees = emp_result.scalars().all()

    # Get today's daily records for these employees
    emp_ids = [e.id for e in employees]
    records_result = await db.execute(
        select(DailyAttendance).where(
            DailyAttendance.employee_id.in_(emp_ids),
            DailyAttendance.date == today,
        )
    )
    records_map = {r.employee_id: r for r in records_result.scalars().all()}

    items = []
    for emp in employees:
        record = records_map.get(emp.id)
        if record:
            items.append(DailyAttendanceOut(
                id=record.id,
                employee_id=emp.id,
                employee_name=emp.full_name,
                date=today,
                punch_in=record.punch_in,
                punch_out=record.punch_out,
                hours_worked=record.hours_worked,
                late_by_minutes=record.late_by_minutes,
                status=record.status,
                is_late=record.is_late,
                is_corrected=record.is_corrected,
                correction_note=record.correction_note,
            ))
        else:
            # Employee has no record yet — show as absent
            from uuid import uuid4
            items.append(DailyAttendanceOut(
                id=uuid4(),
                employee_id=emp.id,
                employee_name=emp.full_name,
                date=today,
                punch_in=None,
                punch_out=None,
                hours_worked=0.0,
                late_by_minutes=0,
                status=DailyStatus.ABSENT,
                is_late=False,
                is_corrected=False,
                correction_note=None,
            ))

    return sorted(items, key=lambda x: x.employee_name)


@router.get("/me", response_model=PaginatedAttendance)
async def my_attendance(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=31, ge=1, le=100),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
):
    """Employee views their own attendance history."""
    from sqlalchemy import func as sqlfunc

    query = select(DailyAttendance).where(
        DailyAttendance.employee_id == current_user.id
    )
    if date_from:
        query = query.where(DailyAttendance.date >= date_from)
    if date_to:
        query = query.where(DailyAttendance.date <= date_to)

    count_result = await db.execute(
        select(sqlfunc.count()).select_from(query.subquery())
    )
    total = count_result.scalar_one()

    query = query.order_by(DailyAttendance.date.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size)

    result = await db.execute(query)
    records = result.scalars().all()

    items = [
        DailyAttendanceOut(
            id=r.id,
            employee_id=r.employee_id,
            employee_name=current_user.full_name,
            date=r.date,
            punch_in=r.punch_in,
            punch_out=r.punch_out,
            hours_worked=r.hours_worked,
            late_by_minutes=r.late_by_minutes,
            status=r.status,
            is_late=r.is_late,
            is_corrected=r.is_corrected,
            correction_note=r.correction_note,
        )
        for r in records
    ]

    return PaginatedAttendance(total=total, page=page, page_size=page_size, items=items)


@router.get("/summary", response_model=AttendanceSummary)
async def attendance_summary(
    db: DbSession,
    current_user: CurrentUser,
    employee_id: Optional[UUID] = Query(default=None),
    month: int = Query(default=None),
    year: int = Query(default=None),
):
    """
    Monthly attendance summary stats for one employee.
    Employees can only see their own. Admins can specify any employee_id.
    Defaults to current month if month/year not provided.
    """
    from datetime import date as dt_date
    today = dt_date.today()
    target_month = month or today.month
    target_year  = year  or today.year

    # Access control
    if current_user.role == EmployeeRole.EMPLOYEE:
        target_id = current_user.id
    else:
        target_id = employee_id or current_user.id

    svc = AttendanceService(db)
    data = await svc.get_employee_monthly_summary(target_id, target_year, target_month)

    return AttendanceSummary(
        total_working_days=data["total_working_days"],
        days_present=data["days_present"],
        days_absent=data["days_absent"],
        days_late=data["days_late"],
        days_wfh=data["days_wfh"],
        attendance_percentage=data["attendance_percentage"],
        average_hours_per_day=data["average_hours_per_day"],
    )


# ── Manual correction ──────────────────────────────────────────────────────────

@router.post("/correct", status_code=status.HTTP_200_OK)
async def correct_attendance(
    body: AttendanceCorrection,
    db: DbSession, actor: AdminUser, request: Request
):
    """
    Admin manually corrects an attendance record.
    Original AttendanceEvents are preserved unchanged.
    The DailyAttendance record is updated and flagged as corrected.
    All corrections are written to the audit log.
    """
    # Verify employee exists
    emp_result = await db.execute(
        select(Employee).where(Employee.id == body.employee_id)
    )
    employee = emp_result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Managers can only correct their own dept
    if (
        actor.role == EmployeeRole.MANAGER
        and employee.department_id != actor.department_id
    ):
        raise HTTPException(status_code=403, detail="Access denied — different department")

    # Get or create the daily record
    svc = AttendanceService(db)
    daily = await svc._get_or_create_daily(body.employee_id, body.date)

    old_snapshot = {
        "punch_in": str(daily.punch_in),
        "punch_out": str(daily.punch_out),
        "status": daily.status.value if daily.status else None,
    }

    # Apply corrections
    if body.punch_in is not None:
        daily.punch_in = body.punch_in
    if body.punch_out is not None:
        daily.punch_out = body.punch_out
    if body.status is not None:
        daily.status = body.status

    daily.is_corrected = True
    daily.correction_note = body.reason
    daily.corrected_by_id = actor.id

    # Recompute derived fields from new punch times
    if body.status is None:
        await svc._compute_daily_status(daily, employee)

    # Write a manual event to the raw log too (for completeness)
    from app.models.attendance import AttendanceEvent, PunchAction
    from datetime import datetime, timezone, time as dt_time
    if body.punch_in:
        manual_event = AttendanceEvent(
            employee_id=body.employee_id,
            device_id="manual-correction",
            event_time=datetime.combine(body.date, body.punch_in).replace(tzinfo=timezone.utc),
            action=PunchAction.PUNCH_IN,
            is_manual=True,
            correction_note=body.reason,
            corrected_by_id=actor.id,
        )
        db.add(manual_event)

    await AuditService(db).log(
        action="attendance.correct",
        entity_type="daily_attendance",
        entity_id=str(daily.id),
        actor=actor,
        old_value=old_snapshot,
        new_value={"punch_in": str(body.punch_in), "punch_out": str(body.punch_out), "reason": body.reason},
        notes=body.reason,
        request=request,
    )

    return {"message": "Attendance corrected successfully", "date": str(body.date)}
