# app/services/attendance_service.py
# ─────────────────────────────────────────────────────────────
# Core business logic for attendance processing.
# No HTTP here — pure database operations and business rules.
#
# The punch state machine:
#   Employee arrives → punch_in recorded → AttendanceEvent created
#   Employee leaves  → punch_out recorded → AttendanceEvent created
#                                         → DailyAttendance updated
#
# State is determined by: does this employee have an open shift today?
#   Open shift = punch_in exists but punch_out is NULL
# ─────────────────────────────────────────────────────────────

from datetime import datetime, date, time, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from loguru import logger

from app.models.employee import Employee
from app.models.attendance import (
    AttendanceEvent, DailyAttendance,
    PunchAction, DailyStatus
)
from app.models.department import Department
from app.core.config import settings


class AttendanceService:

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Main punch handler ─────────────────────────────────────────────────────

    async def process_punch(
        self,
        employee: Employee,
        device_id: str,
        event_time: datetime,
        confidence_score: float | None = None,
        liveness_score: float | None = None,
    ) -> tuple[PunchAction, DailyAttendance]:
        """
        Determine punch-in or punch-out, create the raw event,
        and update (or create) the daily summary record.

        Returns (action_taken, daily_record).

        Logic:
          1. Look for today's DailyAttendance for this employee
          2. If none exists or punch_in is null  → this is a PUNCH-IN
          3. If punch_in exists but punch_out is null → this is a PUNCH-OUT
          4. If both exist already → treat as PUNCH-IN for a new session
             (edge case: someone left and came back — we record both events
              but only update if the new punch-in is earlier or punch-out later)
        """
        today = event_time.astimezone(timezone.utc).date()

        # ── Get or create today's daily record ────────────────────────────────
        daily = await self._get_or_create_daily(employee.id, today)

        # ── Determine action ──────────────────────────────────────────────────
        if daily.punch_in is None:
            action = PunchAction.PUNCH_IN
        elif daily.punch_out is None:
            action = PunchAction.PUNCH_OUT
        else:
            # Both exist — secondary punch-in (employee left and returned)
            # Update punch_in only if this is earlier than the stored one
            action = PunchAction.PUNCH_IN

        # ── Create the raw immutable event ────────────────────────────────────
        event = AttendanceEvent(
            employee_id=employee.id,
            device_id=device_id,
            event_time=event_time,
            action=action,
            confidence_score=confidence_score,
            liveness_score=liveness_score,
        )
        self.db.add(event)

        # ── Update the daily summary ───────────────────────────────────────────
        local_time = event_time.astimezone(timezone.utc).time()

        if action == PunchAction.PUNCH_IN:
            # Only update punch_in if it's earlier than what we have (or empty)
            if daily.punch_in is None or local_time < daily.punch_in:
                daily.punch_in = local_time
            await self._compute_daily_status(daily, employee)

        elif action == PunchAction.PUNCH_OUT:
            # Only update punch_out if it's later than what we have (or empty)
            if daily.punch_out is None or local_time > daily.punch_out:
                daily.punch_out = local_time
            await self._compute_daily_status(daily, employee)

        await self.db.flush()   # write to DB within current transaction
        logger.info(
            f"Punch processed: {employee.employee_code} → {action.value} "
            f"at {event_time.isoformat()} via {device_id}"
        )
        return action, daily

    # ── Daily record helpers ───────────────────────────────────────────────────

    async def _get_or_create_daily(
        self, employee_id: UUID, for_date: date
    ) -> DailyAttendance:
        """Get today's DailyAttendance, creating it (as ABSENT) if it doesn't exist."""
        result = await self.db.execute(
            select(DailyAttendance).where(
                and_(
                    DailyAttendance.employee_id == employee_id,
                    DailyAttendance.date == for_date,
                )
            )
        )
        daily = result.scalar_one_or_none()

        if daily is None:
            daily = DailyAttendance(
                employee_id=employee_id,
                date=for_date,
                status=DailyStatus.ABSENT,
                hours_worked=0.0,
                late_by_minutes=0,
                is_late=False,
            )
            self.db.add(daily)
            await self.db.flush()   # get the ID assigned

        return daily

    async def _compute_daily_status(
        self, daily: DailyAttendance, employee: Employee
    ) -> None:
        """
        Recompute hours_worked, is_late, late_by_minutes, and status
        from current punch_in / punch_out values.

        Called every time a punch is processed for the day.
        This is idempotent — can be called multiple times safely.
        """
        # ── Get department shift settings ─────────────────────────────────────
        dept = employee.department
        if dept:
            shift_start     = dept.shift_start
            grace_minutes   = dept.late_grace_minutes
        else:
            # Fallback to company defaults if no department assigned
            h, m = map(int, settings.DEFAULT_SHIFT_START.split(":"))
            shift_start   = time(h, m)
            grace_minutes = settings.LATE_GRACE_MINUTES

        # ── Lateness ──────────────────────────────────────────────────────────
        if daily.punch_in is not None:
            # Convert both to minutes-since-midnight for easy arithmetic
            shift_start_mins = shift_start.hour * 60 + shift_start.minute
            punch_in_mins    = daily.punch_in.hour * 60 + daily.punch_in.minute
            late_by = max(0, punch_in_mins - shift_start_mins - grace_minutes)

            daily.late_by_minutes = late_by
            daily.is_late = late_by > 0

        # ── Hours worked ──────────────────────────────────────────────────────
        if daily.punch_in is not None and daily.punch_out is not None:
            pin  = datetime.combine(daily.date, daily.punch_in)
            pout = datetime.combine(daily.date, daily.punch_out)
            if pout > pin:
                delta = pout - pin
                daily.hours_worked = round(delta.total_seconds() / 3600, 2)

        # ── Status ────────────────────────────────────────────────────────────
        if daily.punch_in is None:
            daily.status = DailyStatus.ABSENT
        elif daily.is_late:
            daily.status = DailyStatus.LATE
        elif daily.hours_worked > 0 and daily.hours_worked < 4:
            daily.status = DailyStatus.HALF_DAY
        else:
            daily.status = DailyStatus.PRESENT

    # ── Queries ────────────────────────────────────────────────────────────────

    async def get_todays_present_count(self) -> int:
        """How many employees have punched in today (for admin dashboard)."""
        today = date.today()
        result = await self.db.execute(
            select(DailyAttendance).where(
                and_(
                    DailyAttendance.date == today,
                    DailyAttendance.punch_in.is_not(None),
                )
            )
        )
        return len(result.scalars().all())

    async def get_employee_monthly_summary(
        self, employee_id: UUID, year: int, month: int
    ) -> dict:
        """
        Compute attendance summary for one employee for a given month.
        Returns counts and percentages for the dashboard.
        """
        from calendar import monthrange
        _, days_in_month = monthrange(year, month)
        month_start = date(year, month, 1)
        month_end   = date(year, month, days_in_month)

        result = await self.db.execute(
            select(DailyAttendance).where(
                and_(
                    DailyAttendance.employee_id == employee_id,
                    DailyAttendance.date >= month_start,
                    DailyAttendance.date <= month_end,
                )
            )
        )
        records = result.scalars().all()

        present  = sum(1 for r in records if r.status == DailyStatus.PRESENT)
        late     = sum(1 for r in records if r.status == DailyStatus.LATE)
        absent   = sum(1 for r in records if r.status == DailyStatus.ABSENT)
        wfh      = sum(1 for r in records if r.status == DailyStatus.WFH)
        half_day = sum(1 for r in records if r.status == DailyStatus.HALF_DAY)
        total_hours = sum(r.hours_worked for r in records)

        # Working days = weekdays in the month (excluding future dates)
        today = date.today()
        working_days = sum(
            1 for d in range(1, days_in_month + 1)
            if date(year, month, d).weekday() < 5          # Mon–Fri
            and date(year, month, d) <= today
        )

        attendance_pct = round(
            ((present + late + half_day) / working_days * 100) if working_days > 0 else 0,
            1
        )
        avg_hours = round(total_hours / max(present + late, 1), 2)

        return {
            "total_working_days": working_days,
            "days_present": present,
            "days_late": late,
            "days_absent": absent,
            "days_wfh": wfh,
            "days_half_day": half_day,
            "total_hours": round(total_hours, 2),
            "average_hours_per_day": avg_hours,
            "attendance_percentage": attendance_pct,
        }
