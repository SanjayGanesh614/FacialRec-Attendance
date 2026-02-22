# app/models/employee.py
# ─────────────────────────────────────────────────────────────
# Employee table — central entity of the entire system.
# Holds auth credentials, department assignment, and face enrollment status.
# ─────────────────────────────────────────────────────────────

import uuid
import enum
from datetime import date, datetime, timezone
from sqlalchemy import (
    String, Boolean, Date, DateTime, Enum, ForeignKey, Text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class EmployeeRole(str, enum.Enum):
    """
    String enum so values are stored as readable strings in the DB,
    not integers — makes raw DB inspection much easier.
    str mixin means role.value == role in string comparisons.
    """
    SUPER_ADMIN = "super_admin"
    MANAGER     = "manager"
    EMPLOYEE    = "employee"


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Identity ───────────────────────────────────────────────────────────────
    # employee_code is the human-readable ID shown in the portal (e.g. "EMP001")
    # This is also what the Pi sends in its punch payload as employee_id
    employee_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # ── Auth ───────────────────────────────────────────────────────────────────
    # hashed_password is nullable because future OAuth/SSO employees might not have one
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[EmployeeRole] = mapped_column(
        Enum(EmployeeRole, name="employee_role"),
        nullable=False,
        default=EmployeeRole.EMPLOYEE,
    )

    # ── Department ─────────────────────────────────────────────────────────────
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── Employment info ────────────────────────────────────────────────────────
    joining_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    designation: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ── Face enrollment ────────────────────────────────────────────────────────
    # is_enrolled = True means their face embeddings are in the FAISS DB on the Pi
    is_enrolled: Mapped[bool] = mapped_column(Boolean, default=False)
    # enrollment_pending = True means admin triggered enrollment, Pi hasn't confirmed yet
    enrollment_pending: Mapped[bool] = mapped_column(Boolean, default=False)
    # Optional note e.g. "needs re-enrollment — changed appearance"
    enrollment_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Status ─────────────────────────────────────────────────────────────────
    # Never DELETE employees — deactivate them. Preserves audit trail.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # ── Timestamps ─────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    department: Mapped["Department"] = relationship(   # type: ignore[name-defined]
        "Department",
        back_populates="employees",
        foreign_keys=[department_id],
        lazy="selectin",
    )
    attendance_events: Mapped[list["AttendanceEvent"]] = relationship(  # type: ignore[name-defined]
        "AttendanceEvent",
        back_populates="employee",
        lazy="noload",   # never auto-load — always explicit query
    )
    daily_records: Mapped[list["DailyAttendance"]] = relationship(  # type: ignore[name-defined]
        "DailyAttendance",
        back_populates="employee",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Employee {self.employee_code}: {self.full_name} [{self.role}]>"
