# app/schemas/department.py
from uuid import UUID
from datetime import time
from pydantic import BaseModel, Field


class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    code: str = Field(..., min_length=2, max_length=20, pattern=r"^[A-Z0-9_]+$")
    shift_start: time = time(9, 0)
    shift_end: time = time(18, 0)
    late_grace_minutes: int = Field(default=15, ge=0, le=120)
    min_office_days_per_week: int = Field(default=0, ge=0, le=7)


class DepartmentUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100)
    manager_id: UUID | None = None
    shift_start: time | None = None
    shift_end: time | None = None
    late_grace_minutes: int | None = Field(None, ge=0, le=120)
    min_office_days_per_week: int | None = Field(None, ge=0, le=7)
    is_active: bool | None = None


class DepartmentOut(BaseModel):
    id: UUID
    name: str
    code: str
    manager_id: UUID | None
    shift_start: time
    shift_end: time
    late_grace_minutes: int
    min_office_days_per_week: int
    is_active: bool
    employee_count: int = 0

    model_config = {"from_attributes": True}
