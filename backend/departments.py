# app/api/v1/endpoints/departments.py
from uuid import UUID
from fastapi import APIRouter, HTTPException, status, Request
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.core.dependencies import DbSession, AdminUser, SuperAdmin
from app.models.department import Department
from app.models.employee import Employee
from app.schemas.department import DepartmentCreate, DepartmentUpdate, DepartmentOut
from app.services.audit_service import AuditService

router = APIRouter(prefix="/departments", tags=["Departments"])


@router.get("", response_model=list[DepartmentOut])
async def list_departments(db: DbSession, _: AdminUser):
    """List all departments with employee count. Admin/manager only."""
    result = await db.execute(
        select(Department).order_by(Department.name)
    )
    departments = result.scalars().all()

    out = []
    for dept in departments:
        # Count active employees in each department
        count_result = await db.execute(
            select(func.count(Employee.id)).where(
                Employee.department_id == dept.id,
                Employee.is_active == True,  # noqa: E712
            )
        )
        count = count_result.scalar_one()
        dept_out = DepartmentOut.model_validate(dept)
        dept_out.employee_count = count
        out.append(dept_out)

    return out


@router.post("", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED)
async def create_department(
    body: DepartmentCreate, db: DbSession, actor: SuperAdmin, request: Request
):
    """Create a new department. Super admin only."""
    # Check code uniqueness
    existing = await db.execute(
        select(Department).where(Department.code == body.code.upper())
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Department code '{body.code}' already exists",
        )

    dept = Department(**body.model_dump(), code=body.code.upper())
    db.add(dept)
    await db.flush()

    await AuditService(db).log(
        action="department.create",
        entity_type="department",
        entity_id=str(dept.id),
        actor=actor,
        new_value={"name": dept.name, "code": dept.code},
        request=request,
    )

    return DepartmentOut.model_validate(dept)


@router.get("/{dept_id}", response_model=DepartmentOut)
async def get_department(dept_id: UUID, db: DbSession, _: AdminUser):
    result = await db.execute(select(Department).where(Department.id == dept_id))
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    count_result = await db.execute(
        select(func.count(Employee.id)).where(
            Employee.department_id == dept.id,
            Employee.is_active == True,  # noqa: E712
        )
    )
    out = DepartmentOut.model_validate(dept)
    out.employee_count = count_result.scalar_one()
    return out


@router.patch("/{dept_id}", response_model=DepartmentOut)
async def update_department(
    dept_id: UUID, body: DepartmentUpdate,
    db: DbSession, actor: SuperAdmin, request: Request
):
    """Update department settings. Super admin only."""
    result = await db.execute(select(Department).where(Department.id == dept_id))
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    old_snapshot = {"name": dept.name, "shift_start": str(dept.shift_start)}

    # If assigning a manager, verify the employee exists and is in this dept
    if body.manager_id is not None:
        mgr_result = await db.execute(
            select(Employee).where(Employee.id == body.manager_id)
        )
        manager = mgr_result.scalar_one_or_none()
        if not manager:
            raise HTTPException(status_code=404, detail="Manager employee not found")

    update_data = body.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(dept, key, value)

    await AuditService(db).log(
        action="department.update",
        entity_type="department",
        entity_id=str(dept.id),
        actor=actor,
        old_value=old_snapshot,
        new_value=update_data,
        request=request,
    )

    return DepartmentOut.model_validate(dept)
