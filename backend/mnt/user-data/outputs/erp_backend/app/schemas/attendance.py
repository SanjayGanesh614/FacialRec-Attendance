# app/schemas/attendance.py
from uuid import UUID
from datetime import date, datetime, time
from pydantic import BaseModel, Field
from app.models.attendance import PunchAction, DailyStatus


# ── Pi → Server ────────────────────────────────────────────────────────────────

class PunchRequest(BaseModel):
    """
    Exact payload the Pi sends.
    Must match what erp_client.py sends — don't change field names here
    without updating the Pi code too.
    """
    employee_id: str          # employee_code string e.g. "EMP001"
    device_id: str            # e.g. "pi-door-01"
    timestamp: datetime       # ISO 8601 with timezone from Pi


class PunchResponse(BaseModel):
    """What we send back to the Pi."""
    success: bool
    action: str               # "punch_in" | "punch_out"
    employee_name: str
    message: str


# ── Manual correction (admin only) ────────────────────────────────────────────

class AttendanceCorrection(BaseModel):
    employee_id: UUID
    date: date
    punch_in: time | None = None
    punch_out: time | None = None
    status: DailyStatus | None = None
    reason: str = Field(..., min_length=5, max_length=500)


# ── Query responses ────────────────────────────────────────────────────────────

class AttendanceEventOut(BaseModel):
    id: UUID
    employee_id: UUID
    employee_name: str
    device_id: str
    event_time: datetime
    action: PunchAction
    confidence_score: float | None
    liveness_score: float | None
    is_manual: bool
    correction_note: str | None

    model_config = {"from_attributes": True}


class DailyAttendanceOut(BaseModel):
    id: UUID
    employee_id: UUID
    employee_name: str
    date: date
    punch_in: time | None
    punch_out: time | None
    hours_worked: float
    late_by_minutes: int
    status: DailyStatus
    is_late: bool
    is_corrected: bool
    correction_note: str | None

    model_config = {"from_attributes": True}


class PaginatedAttendance(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[DailyAttendanceOut]


class AttendanceSummary(BaseModel):
    """Quick stats — used on dashboards."""
    total_working_days: int
    days_present: int
    days_absent: int
    days_late: int
    days_wfh: int
    attendance_percentage: float
    average_hours_per_day: float
