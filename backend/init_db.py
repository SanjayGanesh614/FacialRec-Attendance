# app/db/init_db.py
# ─────────────────────────────────────────────────────────────
# First-run database seeding.
# Called once at application startup.
# Creates the super admin account if no employees exist yet.
# Safe to call multiple times — checks before creating.
# ─────────────────────────────────────────────────────────────

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from loguru import logger

from app.models.employee import Employee, EmployeeRole
from app.core.security import hash_password
from app.core.config import settings


async def init_db(db: AsyncSession) -> None:
    """
    Seed the database on first run.
    Called from app startup event in main.py.
    """
    # Check if any employees exist
    result = await db.execute(select(func.count(Employee.id)))
    count = result.scalar_one()

    if count > 0:
        logger.info(f"Database already seeded ({count} employees found). Skipping.")
        return

    logger.info("First run detected — seeding super admin account...")

    admin = Employee(
        employee_code="EMP0001",
        full_name=settings.FIRST_ADMIN_NAME,
        email=settings.FIRST_ADMIN_EMAIL.lower(),
        hashed_password=hash_password(settings.FIRST_ADMIN_PASSWORD),
        role=EmployeeRole.SUPER_ADMIN,
        is_enrolled=False,
        is_active=True,
    )
    db.add(admin)
    await db.commit()

    logger.success(
        f"Super admin created: {settings.FIRST_ADMIN_EMAIL} "
        f"(CHANGE THE PASSWORD IMMEDIATELY after first login)"
    )
