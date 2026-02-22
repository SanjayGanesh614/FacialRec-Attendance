# app/models/attendance.py
# ─────────────────────────────────────────────────────────────
# Two attendance tables:
#
# 1. AttendanceEvent  — immutable raw log of every single punch
#    (one row per Pi recognition event)
#
# 2. DailyAttendance  — computed daily summary per employee
#    (one row per employee per working day)
#    Built/updated whenever a new AttendanceEvent arrives.
#
# Why two tables?
#   Raw events are the ground truth and must never be altered.
#   Daily records are derived and can be recomputed.
#   Dashboards and reports always read from DailyAttendance for speed.
#   Corrections are applied to DailyAttendance only, with a note linking
#   back to the corrector in the audit log.
# ─────────────────────────────────────────────────────────────

import uuid
import enum
from datetime import date, datetime, timezone, time
from sqlalchemy import (
    String, Boolean, Date, DateTime, Enum, Float,
    ForeignKey, Integer, Text, Time, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class PunchAction(str, enum.Enum):
    PUNCH_IN  = "punch_in"
    PUNCH_OUT = "punch_out"


class DailyStatus(str, enum.Enum):
    PRESENT  = "present"    # punched in and met minimum hours
    ABSENT   = "absent"     # no punch events for this day
    LATE     = "late"       # punched in after grace period
    HALF_DAY = "half_day"   # punched in but left very early
    WFH      = "wfh"        # employee marked WFH (from schedule intent)
    LEAVE    = "leave"      # approved leave
    HOLIDAY  = "holiday"    # company holiday


# ── Raw event log ──────────────────────────────────────────────────────────────

class AttendanceEvent(Base):
    __tablename__ = "attendance_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="RESTRICT"),  # never cascade delete
        nullable=False,
        index=True,
    )
    # Which Pi terminal captured this event
    device_id: Mapped[str] = mapped_column(String(50), nullable=False)
    # The exact time the Pi sent the event (UTC, timezone-aware)
    event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    action: Mapped[PunchAction] = mapped_column(
        Enum(PunchAction, name="punch_action"), nullable=False
    )

    # ML model metadata — useful for auditing and threshold tuning
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    liveness_score: Mapped[float | None]   = mapped_column(Float, nullable=True)

    # Manual correction fields
    # is_manual=True means an admin added this row, not the Pi
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False)
    correction_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrected_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    employee: Mapped["Employee"] = relationship(  # type: ignore[name-defined]
        "Employee",
        back_populates="attendance_events",
        foreign_keys=[employee_id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<AttendanceEvent {self.action} {self.employee_id} @ {self.event_time}>"


# ── Computed daily summary ─────────────────────────────────────────────────────

class DailyAttendance(Base):
    __tablename__ = "daily_attendance"
    __table_args__ = (
        # One row per employee per date — enforced at DB level
        UniqueConstraint("employee_id", "date", name="uq_daily_attendance_emp_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # First punch-in and last punch-out of the day (local time stored as Time)
    punch_in:  Mapped[time | None] = mapped_column(Time, nullable=True)
    punch_out: Mapped[time | None] = mapped_column(Time, nullable=True)

    # Computed from punch times — stored so reports don't recalculate every time
    hours_worked: Mapped[float] = mapped_column(Float, default=0.0)
    # Minutes late compared to shift_start + grace period (0 if on time)
    late_by_minutes: Mapped[int] = mapped_column(Integer, default=0)

    status: Mapped[DailyStatus] = mapped_column(
        Enum(DailyStatus, name="daily_status"),
        nullable=False,
        default=DailyStatus.ABSENT,
    )
    is_late: Mapped[bool] = mapped_column(Boolean, default=False)

    # If admin manually corrected this record
    is_corrected: Mapped[bool] = mapped_column(Boolean, default=False)
    correction_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrected_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    employee: Mapped["Employee"] = relationship(  # type: ignore[name-defined]
        "Employee",
        back_populates="daily_records",
        foreign_keys=[employee_id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<DailyAttendance {self.employee_id} {self.date}: {self.status}>"
