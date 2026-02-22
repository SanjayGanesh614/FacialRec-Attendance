# app/services/reports_service.py
# ─────────────────────────────────────────────────────────────
# Pure aggregation logic for Phase 4 reports.
# No HTTP here — takes a DB session, returns dataclasses/dicts.
#
# Designed to be called from the /reports/* endpoints.
# Heavy queries are kept as single SQL statements where possible
# to avoid N+1 patterns that would be painful at scale.
# ─────────────────────────────────────────────────────────────

import calendar
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.models.attendance import DailyAttendance, DailyStatus
from app.models.employee import Employee
from app.models.department import Department


class ReportsService:

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Daily EOD report ───────────────────────────────────────────────────────

    async def get_daily_report(
        self, for_date: date, department_id: UUID | None = None
    ) -> dict:
        """
        Full attendance snapshot for one date.
        Returns rows for every active employee — present, absent, or otherwise.
        """
        # Get all active employees (with optional dept filter)
        emp_q = select(Employee).where(Employee.is_active == True)  # noqa: E712
        if department_id:
            emp_q = emp_q.where(Employee.department_id == department_id)
        emp_result = await self.db.execute(emp_q)
        employees = emp_result.scalars().all()

        # Get that day's attendance records
        emp_ids = [e.id for e in employees]
        att_result = await self.db.execute(
            select(DailyAttendance).where(
                DailyAttendance.employee_id.in_(emp_ids),
                DailyAttendance.date == for_date,
            )
        )
        att_map = {r.employee_id: r for r in att_result.scalars().all()}

        # Department name cache
        dept_ids = {e.department_id for e in employees if e.department_id}
        dept_result = await self.db.execute(
            select(Department).where(Department.id.in_(dept_ids))
        )
        dept_map = {d.id: d.name for d in dept_result.scalars().all()}

        rows = []
        for emp in sorted(employees, key=lambda e: e.full_name):
            att = att_map.get(emp.id)
            rows.append({
                "employee_id":    emp.id,
                "employee_code":  emp.employee_code,
                "employee_name":  emp.full_name,
                "department_name": dept_map.get(emp.department_id) if emp.department_id else None,
                "punch_in":       att.punch_in if att else None,
                "punch_out":      att.punch_out if att else None,
                "hours_worked":   att.hours_worked if att else 0.0,
                "late_by_minutes": att.late_by_minutes if att else 0,
                "status":         att.status if att else DailyStatus.ABSENT,
                "is_late":        att.is_late if att else False,
                "is_corrected":   att.is_corrected if att else False,
            })

        # Summary stats
        statuses = [r["status"] for r in rows]
        present  = statuses.count(DailyStatus.PRESENT) + statuses.count(DailyStatus.LATE)
        absent   = statuses.count(DailyStatus.ABSENT)
        late     = statuses.count(DailyStatus.LATE)
        wfh      = statuses.count(DailyStatus.WFH)
        half_day = statuses.count(DailyStatus.HALF_DAY)
        total    = len(rows)
        hours_list = [r["hours_worked"] for r in rows if r["hours_worked"] > 0]

        return {
            "date":           for_date,
            "total_employees": total,
            "present":        present,
            "absent":         absent,
            "late":           late,
            "wfh":            wfh,
            "half_day":       half_day,
            "attendance_pct": round(present / total * 100, 1) if total else 0.0,
            "average_hours":  round(sum(hours_list) / len(hours_list), 2) if hours_list else 0.0,
            "rows":           rows,
        }

    # ── Monthly employee report ────────────────────────────────────────────────

    async def get_monthly_employee_report(
        self, employee_id: UUID, year: int, month: int
    ) -> dict:
        """
        Day-by-day attendance for one employee in a month.
        Used to render the monthly calendar heatmap and stats sidebar.
        """
        emp_result = await self.db.execute(
            select(Employee).where(Employee.id == employee_id)
        )
        employee = emp_result.scalar_one_or_none()
        if not employee:
            return {}

        dept_name = None
        if employee.department_id:
            dept_result = await self.db.execute(
                select(Department).where(Department.id == employee.department_id)
            )
            dept = dept_result.scalar_one_or_none()
            dept_name = dept.name if dept else None

        _, days_in_month = calendar.monthrange(year, month)
        month_start = date(year, month, 1)
        month_end   = date(year, month, days_in_month)

        att_result = await self.db.execute(
            select(DailyAttendance).where(
                DailyAttendance.employee_id == employee_id,
                DailyAttendance.date >= month_start,
                DailyAttendance.date <= month_end,
            ).order_by(DailyAttendance.date)
        )
        records = att_result.scalars().all()
        att_map = {r.date: r for r in records}

        today = date.today()
        days = []
        for d in range(1, days_in_month + 1):
            dt = date(year, month, d)
            if dt > today:
                continue
            att = att_map.get(dt)
            days.append({
                "date":          dt,
                "status":        att.status if att else DailyStatus.ABSENT,
                "punch_in":      att.punch_in if att else None,
                "punch_out":     att.punch_out if att else None,
                "hours_worked":  att.hours_worked if att else 0.0,
                "late_by_minutes": att.late_by_minutes if att else 0,
                "is_corrected":  att.is_corrected if att else False,
            })

        # Working days = weekdays up to today
        working_days = sum(
            1 for d in range(1, days_in_month + 1)
            if date(year, month, d).weekday() < 5 and date(year, month, d) <= today
        )

        statuses     = [d["status"] for d in days]
        present      = statuses.count(DailyStatus.PRESENT)
        late         = statuses.count(DailyStatus.LATE)
        absent_days  = working_days - present - late - statuses.count(DailyStatus.WFH) - statuses.count(DailyStatus.HALF_DAY)
        wfh          = statuses.count(DailyStatus.WFH)
        half_day     = statuses.count(DailyStatus.HALF_DAY)
        total_hours  = sum(d["hours_worked"] for d in days)
        worked_days  = present + late + half_day
        att_pct      = round((present + late + half_day) / working_days * 100, 1) if working_days else 0.0

        return {
            "employee_id":    employee.id,
            "employee_code":  employee.employee_code,
            "employee_name":  employee.full_name,
            "department_name": dept_name,
            "month":          month,
            "year":           year,
            "total_working_days": working_days,
            "days_present":   present,
            "days_absent":    max(absent_days, 0),
            "days_late":      late,
            "days_wfh":       wfh,
            "days_half_day":  half_day,
            "total_hours":    round(total_hours, 2),
            "average_hours":  round(total_hours / worked_days, 2) if worked_days else 0.0,
            "attendance_pct": att_pct,
            "days":           days,
        }

    # ── Department comparison ──────────────────────────────────────────────────

    async def get_department_comparison(self, year: int, month: int) -> dict:
        """
        Side-by-side stats for every department for a given month.
        Used by the comparison bar chart on the admin reports page.
        """
        _, days_in_month = calendar.monthrange(year, month)
        month_start = date(year, month, 1)
        month_end   = date(year, month, days_in_month)
        today       = date.today()

        depts_result = await self.db.execute(
            select(Department).where(Department.is_active == True)  # noqa: E712
        )
        departments = depts_result.scalars().all()

        result = []
        for dept in departments:
            # Get active employees in dept
            emps_result = await self.db.execute(
                select(Employee).where(
                    Employee.department_id == dept.id,
                    Employee.is_active == True,  # noqa: E712
                )
            )
            emp_ids = [e.id for e in emps_result.scalars().all()]
            if not emp_ids:
                continue

            # Get attendance for this month
            att_result = await self.db.execute(
                select(DailyAttendance).where(
                    DailyAttendance.employee_id.in_(emp_ids),
                    DailyAttendance.date >= month_start,
                    DailyAttendance.date <= min(month_end, today),
                )
            )
            records = att_result.scalars().all()

            present  = sum(1 for r in records if r.status in (DailyStatus.PRESENT, DailyStatus.LATE))
            absent   = sum(1 for r in records if r.status == DailyStatus.ABSENT)
            late     = sum(1 for r in records if r.status == DailyStatus.LATE)
            hours    = [r.hours_worked for r in records if r.hours_worked > 0]

            # Working days so far this month
            working_days = sum(
                1 for d in range(1, days_in_month + 1)
                if date(year, month, d).weekday() < 5 and date(year, month, d) <= today
            )
            total_possible = working_days * len(emp_ids)
            att_pct = round(present / total_possible * 100, 1) if total_possible else 0.0

            result.append({
                "department_id":   dept.id,
                "department_name": dept.name,
                "department_code": dept.code,
                "employee_count":  len(emp_ids),
                "days_present":    present,
                "days_absent":     absent,
                "days_late":       late,
                "attendance_pct":  att_pct,
                "average_hours":   round(sum(hours) / len(hours), 2) if hours else 0.0,
            })

        return {"month": month, "year": year, "departments": result}

    # ── Attendance trend (6-month) ─────────────────────────────────────────────

    async def get_attendance_trend(
        self, months: int = 6, employee_id: UUID | None = None
    ) -> dict:
        """
        Build trend data for the last N months.
        If employee_id is given, returns that person's trend.
        Otherwise returns company-wide averages.
        """
        MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun',
                       'Jul','Aug','Sep','Oct','Nov','Dec']
        today  = date.today()
        points = []

        for offset in range(months - 1, -1, -1):
            # Go back `offset` months from today
            m = today.month - offset
            y = today.year
            while m <= 0:
                m += 12
                y -= 1

            _, days_in_month = calendar.monthrange(y, m)
            m_start = date(y, m, 1)
            m_end   = date(y, m, days_in_month)

            if employee_id:
                att_result = await self.db.execute(
                    select(DailyAttendance).where(
                        DailyAttendance.employee_id == employee_id,
                        DailyAttendance.date >= m_start,
                        DailyAttendance.date <= min(m_end, today),
                    )
                )
                records = att_result.scalars().all()
            else:
                att_result = await self.db.execute(
                    select(DailyAttendance).where(
                        DailyAttendance.date >= m_start,
                        DailyAttendance.date <= min(m_end, today),
                    )
                )
                records = att_result.scalars().all()

            present = sum(1 for r in records if r.status in (DailyStatus.PRESENT, DailyStatus.LATE))
            absent  = sum(1 for r in records if r.status == DailyStatus.ABSENT)
            late    = sum(1 for r in records if r.status == DailyStatus.LATE)
            total   = present + absent
            att_pct = round(present / total * 100, 1) if total else 0.0

            points.append({
                "month": m,
                "year":  y,
                "label": f"{MONTH_NAMES[m - 1]} {y}",
                "attendance_pct": att_pct,
                "days_present":   present,
                "days_absent":    absent,
                "days_late":      late,
            })

        return {"employee_id": employee_id, "points": points}

    # ── CSV export ─────────────────────────────────────────────────────────────

    async def build_csv(
        self, date_from: date, date_to: date,
        employee_id: UUID | None = None,
        department_id: UUID | None = None,
    ) -> str:
        """
        Build a CSV string for a date range.
        Used by the download endpoint — returns raw CSV text.
        """
        query = select(DailyAttendance).where(
            DailyAttendance.date >= date_from,
            DailyAttendance.date <= date_to,
        )

        if employee_id:
            query = query.where(DailyAttendance.employee_id == employee_id)
        elif department_id:
            query = (
                query.join(Employee, DailyAttendance.employee_id == Employee.id)
                     .where(Employee.department_id == department_id)
            )

        query = query.order_by(DailyAttendance.date, DailyAttendance.employee_id)
        result = await self.db.execute(query)
        records = result.scalars().all()

        # Build employee name map
        emp_ids = list({r.employee_id for r in records})
        emp_result = await self.db.execute(
            select(Employee).where(Employee.id.in_(emp_ids))
        )
        emp_map = {e.id: (e.full_name, e.employee_code) for e in emp_result.scalars().all()}

        lines = ["Date,Employee Code,Employee Name,Punch In,Punch Out,Hours Worked,Late By (mins),Status,Corrected"]
        for r in records:
            name, code = emp_map.get(r.employee_id, ("Unknown", "—"))
            lines.append(
                f"{r.date},{code},{name},"
                f"{str(r.punch_in)[:5] if r.punch_in else ''},"
                f"{str(r.punch_out)[:5] if r.punch_out else ''},"
                f"{r.hours_worked:.2f},{r.late_by_minutes},"
                f"{r.status.value},{'Yes' if r.is_corrected else 'No'}"
            )

        return "\n".join(lines)
