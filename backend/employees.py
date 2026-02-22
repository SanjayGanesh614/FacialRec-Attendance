# app/api/v1/endpoints/employees.py
# ─────────────────────────────────────────────────────────────
# Employee CRUD endpoints.
# Also handles triggering face enrollment via the portal.
# ─────────────────────────────────────────────────────────────

from uuid import UUID
from fastapi import APIRouter, HTTPException, status, Query, Request
from sqlalchemy import select, or_, func
from sqlalchemy.orm import selectinload

from app.core.dependencies import DbSession, CurrentUser, AdminUser, SuperAdmin
from app.core.security import hash_password
from app.models.employee import Employee, EmployeeRole
from app.models.department import Department
from app.schemas.employee import (
    EmployeeCreate, EmployeeUpdate, EmployeeOut,
    EmployeeListItem, PaginatedEmployees, EmployeePasswordChange
)
from app.services.audit_service import AuditService

router = APIRouter(prefix="/employees", tags=["Employees"])


def _generate_employee_code(db_count: int) -> str:
    """Simple sequential code generator: EMP001, EMP002, ..."""
    return f"EMP{(db_count + 1):04d}"


@router.get("", response_model=PaginatedEmployees)
async def list_employees(
    db: DbSession,
    _: AdminUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    search: str | None = Query(default=None),
    department_id: UUID | None = Query(default=None),
    role: EmployeeRole | None = Query(default=None),
    is_active: bool = Query(default=True),
):
    """
    Paginated employee list. Filterable by search term, department, role.
    Admin/manager only.
    """
    query = select(Employee).where(Employee.is_active == is_active)  # noqa: E712

    if search:
        term = f"%{search}%"
        query = query.where(
            or_(
                Employee.full_name.ilike(term),
                Employee.email.ilike(term),
                Employee.employee_code.ilike(term),
            )
        )
    if department_id:
        query = query.where(Employee.department_id == department_id)
    if role:
        query = query.where(Employee.role == role)

    # Total count (for pagination metadata)
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar_one()

    # Paginated results
    query = query.order_by(Employee.full_name).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    employees = result.scalars().all()

    items = [
        EmployeeListItem(
            id=emp.id,
            employee_code=emp.employee_code,
            full_name=emp.full_name,
            email=emp.email,
            role=emp.role,
            department_name=emp.department.name if emp.department else None,
            is_enrolled=emp.is_enrolled,
            is_active=emp.is_active,
        )
        for emp in employees
    ]

    return PaginatedEmployees(total=total, page=page, page_size=page_size, items=items)


@router.post("", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
async def create_employee(
    body: EmployeeCreate, db: DbSession, actor: SuperAdmin, request: Request
):
    """
    Create a new employee.
    Auto-generates employee_code if not provided.
    Super admin only — managers cannot create employees.
    """
    # Check email uniqueness
    existing_email = await db.execute(
        select(Employee).where(Employee.email == body.email.lower())
    )
    if existing_email.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An employee with this email already exists",
        )

    # Validate department exists if provided
    if body.department_id:
        dept_result = await db.execute(
            select(Department).where(Department.id == body.department_id)
        )
        if not dept_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Department not found")

    # Auto-generate employee_code if not provided
    if not body.employee_code:
        count_result = await db.execute(select(func.count(Employee.id)))
        total = count_result.scalar_one()
        employee_code = _generate_employee_code(total)
    else:
        employee_code = body.employee_code.upper()
        # Check code uniqueness
        code_existing = await db.execute(
            select(Employee).where(Employee.employee_code == employee_code)
        )
        if code_existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Employee code '{employee_code}' already exists",
            )

    employee = Employee(
        employee_code=employee_code,
        full_name=body.full_name,
        email=body.email.lower(),
        hashed_password=hash_password(body.password),
        role=body.role,
        department_id=body.department_id,
        phone=body.phone,
        joining_date=body.joining_date,
        designation=body.designation,
    )
    db.add(employee)
    await db.flush()

    await AuditService(db).log(
        action="employee.create",
        entity_type="employee",
        entity_id=str(employee.id),
        actor=actor,
        new_value={
            "employee_code": employee.employee_code,
            "name": employee.full_name,
            "email": employee.email,
            "role": employee.role.value,
        },
        request=request,
    )

    return EmployeeOut.model_validate(employee)


@router.get("/{employee_id}", response_model=EmployeeOut)
async def get_employee(
    employee_id: UUID, db: DbSession, current_user: CurrentUser
):
    """
    Get one employee's full profile.
    Employees can only see their own profile.
    Admins/managers can see anyone.
    """
    result = await db.execute(
        select(Employee).where(Employee.id == employee_id)
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Employees can only access their own record
    if (
        current_user.role == EmployeeRole.EMPLOYEE
        and current_user.id != employee_id
    ):
        raise HTTPException(status_code=403, detail="Access denied")

    return EmployeeOut.model_validate(employee)


@router.patch("/{employee_id}", response_model=EmployeeOut)
async def update_employee(
    employee_id: UUID, body: EmployeeUpdate,
    db: DbSession, actor: AdminUser, request: Request
):
    """Update employee details. Admin/manager only."""
    result = await db.execute(
        select(Employee).where(Employee.id == employee_id)
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Managers can only update employees in their department
    if (
        actor.role == EmployeeRole.MANAGER
        and employee.department_id != actor.department_id
    ):
        raise HTTPException(
            status_code=403, detail="Managers can only update their own department's employees"
        )

    old_snapshot = {"name": employee.full_name, "role": employee.role.value}

    if body.email:
        body_dict = body.model_dump(exclude_none=True)
        body_dict["email"] = body.email.lower()
    else:
        body_dict = body.model_dump(exclude_none=True)

    for key, value in body_dict.items():
        setattr(employee, key, value)

    await AuditService(db).log(
        action="employee.update",
        entity_type="employee",
        entity_id=str(employee.id),
        actor=actor,
        old_value=old_snapshot,
        new_value=body_dict,
        request=request,
    )

    return EmployeeOut.model_validate(employee)


@router.post("/{employee_id}/enroll", status_code=status.HTTP_202_ACCEPTED)
async def trigger_enrollment(
    employee_id: UUID, db: DbSession, actor: SuperAdmin, request: Request
):
    """
    Signal that this employee needs face enrollment.
    Sets enrollment_pending=True — the Pi polls for this flag
    at /devices/embeddings/sync and enters enrollment mode for this person.
    Returns 202 Accepted (not 200) because enrollment happens asynchronously.
    """
    result = await db.execute(
        select(Employee).where(Employee.id == employee_id)
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    employee.enrollment_pending = True

    await AuditService(db).log(
        action="employee.enrollment_triggered",
        entity_type="employee",
        entity_id=str(employee.id),
        actor=actor,
        notes=f"Enrollment triggered for {employee.full_name} ({employee.employee_code})",
        request=request,
    )

    return {
        "message": f"Enrollment queued for {employee.full_name}",
        "employee_code": employee.employee_code,
        "status": "pending",
    }


@router.post("/{employee_id}/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    employee_id: UUID, body: EmployeePasswordChange,
    db: DbSession, current_user: CurrentUser
):
    """
    Employees can change their own password.
    Admins can change any password (they skip the current_password check).
    """
    result = await db.execute(
        select(Employee).where(Employee.id == employee_id)
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Non-admin changing someone else's password is forbidden
    if current_user.role == EmployeeRole.EMPLOYEE and current_user.id != employee_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Employees must verify their current password
    if current_user.role == EmployeeRole.EMPLOYEE:
        from app.core.security import verify_password
        if not verify_password(body.current_password, employee.hashed_password or ""):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

    employee.hashed_password = hash_password(body.new_password)
    return None
