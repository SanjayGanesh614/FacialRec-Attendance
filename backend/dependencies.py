# app/core/dependencies.py
# ─────────────────────────────────────────────────────────────
# FastAPI Depends() functions.
# These are injected into route handlers to handle:
#   • Database session lifecycle
#   • JWT authentication
#   • Role-based access control
#   • Pi device API key verification
#
# Usage in a route:
#   async def my_route(
#       db: AsyncSession = Depends(get_db),
#       current_user: Employee = Depends(require_admin),
#   ):
# ─────────────────────────────────────────────────────────────

from uuid import UUID
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.core.security import verify_access_token
from app.core.config import settings
from app.models.employee import Employee, EmployeeRole

# ── HTTP Bearer scheme (reads Authorization: Bearer <token>) ──
_bearer_scheme = HTTPBearer(auto_error=False)

# ── X-Api-Key header scheme (used by Pi devices) ──────────────
_device_key_scheme = APIKeyHeader(name="X-Api-Key", auto_error=False)


# ── Database session ──────────────────────────────────────────────────────────

async def get_db():
    """
    Yields a fresh async DB session per request.
    Automatically commits on success, rolls back on exception.

    Always use this via Depends() — never create sessions manually in routes.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Current authenticated user ─────────────────────────────────────────────────

async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(_bearer_scheme)
    ],
    db: AsyncSession = Depends(get_db),
) -> Employee:
    """
    Extract and verify JWT from Authorization header.
    Returns the Employee ORM object for the authenticated user.
    Raises 401 if token is missing, expired, or invalid.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise credentials_exception

    payload = verify_access_token(credentials.credentials)
    if payload is None:
        raise credentials_exception

    employee_id_str: str = payload.get("sub")
    if not employee_id_str:
        raise credentials_exception

    try:
        employee_id = UUID(employee_id_str)
    except ValueError:
        raise credentials_exception

    # Fetch from DB — this also catches deactivated accounts
    result = await db.execute(
        select(Employee).where(
            Employee.id == employee_id,
            Employee.is_active == True,   # noqa: E712 — SQLAlchemy needs ==
        )
    )
    employee = result.scalar_one_or_none()

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account not found or deactivated",
        )

    return employee


# ── Role guards ────────────────────────────────────────────────────────────────

async def require_admin(
    current_user: Employee = Depends(get_current_user),
) -> Employee:
    """Only super admins can proceed. Raises 403 otherwise."""
    if current_user.role not in (EmployeeRole.SUPER_ADMIN, EmployeeRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions — admin or manager required",
        )
    return current_user


async def require_super_admin(
    current_user: Employee = Depends(get_current_user),
) -> Employee:
    """Only super admins — not managers — can proceed."""
    if current_user.role != EmployeeRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions — super admin only",
        )
    return current_user


# ── Pi device authentication ───────────────────────────────────────────────────

async def verify_device_key(
    api_key: Annotated[str | None, Security(_device_key_scheme)],
) -> str:
    """
    Validates the X-Api-Key header sent by Pi devices.
    This is a shared secret — all registered Pi devices use the same key.

    Returns the key string on success (can be used to log the authenticated device).
    Raises 401 on missing or wrong key.

    Note: In Phase 6 we can upgrade this to per-device keys stored in DB.
    """
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Api-Key header",
        )
    if api_key != settings.DEVICE_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid device API key",
        )
    return api_key


# ── Convenience type aliases ───────────────────────────────────────────────────
# Use these in route signatures for cleaner code:
#   async def my_route(db: DbSession, user: CurrentUser): ...

DbSession    = Annotated[AsyncSession, Depends(get_db)]
CurrentUser  = Annotated[Employee, Depends(get_current_user)]
AdminUser    = Annotated[Employee, Depends(require_admin)]
SuperAdmin   = Annotated[Employee, Depends(require_super_admin)]
DeviceAuth   = Annotated[str, Depends(verify_device_key)]
