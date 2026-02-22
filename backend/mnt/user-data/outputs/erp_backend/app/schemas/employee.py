# app/schemas/employee.py
from uuid import UUID
from datetime import date, datetime
from pydantic import BaseModel, EmailStr, Field
from app.models.employee import EmployeeRole


class EmployeeCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: EmployeeRole = EmployeeRole.EMPLOYEE
    department_id: UUID | None = None
    phone: str | None = None
    joining_date: date | None = None
    designation: str | None = None
    # employee_code is auto-generated if not provided
    employee_code: str | None = Field(None, pattern=r"^[A-Z0-9\-]+$", max_length=20)


class EmployeeUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=2, max_length=150)
    email: EmailStr | None = None
    phone: str | None = None
    role: EmployeeRole | None = None
    department_id: UUID | None = None
    joining_date: date | None = None
    designation: str | None = None
    is_active: bool | None = None
    enrollment_notes: str | None = None


class EmployeePasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


# ── Response schemas ────────────────────────────────────────────────────────────

class DepartmentSummary(BaseModel):
    id: UUID
    name: str
    code: str
    model_config = {"from_attributes": True}


class EmployeeOut(BaseModel):
    """Full detail — used on /employees/{id} and own profile."""
    id: UUID
    employee_code: str
    full_name: str
    email: str
    phone: str | None
    role: EmployeeRole
    department: DepartmentSummary | None
    joining_date: date | None
    designation: str | None
    is_enrolled: bool
    enrollment_pending: bool
    enrollment_notes: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class EmployeeListItem(BaseModel):
    """Lighter version for list responses — avoids loading heavy relations."""
    id: UUID
    employee_code: str
    full_name: str
    email: str
    role: EmployeeRole
    department_name: str | None = None
    is_enrolled: bool
    is_active: bool

    model_config = {"from_attributes": True}


class PaginatedEmployees(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[EmployeeListItem]
