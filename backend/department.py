# app/models/department.py
# ─────────────────────────────────────────────────────────────
# Department table.
# A department has a manager (one employee FK) and policy settings.
# Departments must exist before employees can be assigned to them.
# ─────────────────────────────────────────────────────────────

import uuid
from datetime import time
from sqlalchemy import String, Integer, Time, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)

    # FK to the employee who manages this dept.
    # nullable=True because: admin creates dept first, assigns manager after.
    # Also avoids circular FK issues at table creation.
    manager_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Attendance policy (can be overridden per dept) ─────────────────────────
    # Shift start/end — used to calculate late arrivals and hours worked
    shift_start: Mapped[time] = mapped_column(Time, default=time(9, 0))
    shift_end: Mapped[time] = mapped_column(Time, default=time(18, 0))
    # Minutes after shift_start before someone is flagged as late
    late_grace_minutes: Mapped[int] = mapped_column(Integer, default=15)
    # Minimum office days per week required (for hybrid policy tracking)
    min_office_days_per_week: Mapped[int] = mapped_column(Integer, default=0)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    # back_populates links to Employee.department
    # lazy="selectin" loads employees alongside the department in one query
    employees: Mapped[list["Employee"]] = relationship(   # type: ignore[name-defined]
        "Employee",
        back_populates="department",
        foreign_keys="Employee.department_id",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Department {self.code}: {self.name}>"
