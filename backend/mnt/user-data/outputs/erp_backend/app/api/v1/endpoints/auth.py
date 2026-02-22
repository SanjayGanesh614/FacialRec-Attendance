# app/api/v1/endpoints/auth.py
# ─────────────────────────────────────────────────────────────
# Authentication endpoints:
#   POST /auth/login    — exchange email+password for tokens
#   POST /auth/refresh  — exchange refresh token for new access token
#   GET  /auth/me       — get current user's profile
#   POST /auth/logout   — (stateless JWT — just a client-side hint)
# ─────────────────────────────────────────────────────────────

from fastapi import APIRouter, HTTPException, status, Request
from sqlalchemy import select

from app.core.dependencies import DbSession, CurrentUser
from app.core.security import (
    verify_password, create_access_token, create_refresh_token, verify_refresh_token
)
from app.models.employee import Employee
from app.schemas.auth import (
    LoginRequest, TokenResponse, RefreshRequest,
    AccessTokenResponse, MeResponse
)
from app.services.audit_service import AuditService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: DbSession, request: Request):
    """
    Exchange email + password for an access token and refresh token.

    Access tokens are short-lived (60 min default).
    Refresh tokens are long-lived (30 days default).
    Store both on the client; use the refresh token to get a new access token
    without re-entering credentials.
    """
    # Find the employee by email
    result = await db.execute(
        select(Employee).where(
            Employee.email == body.email.lower(),
            Employee.is_active == True,   # noqa: E712
        )
    )
    employee = result.scalar_one_or_none()

    # Use constant-time comparison even on "not found" case to prevent
    # timing attacks that reveal whether an email exists
    if employee is None or not verify_password(body.password, employee.hashed_password or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token  = create_access_token(employee.id, employee.role.value)
    refresh_token = create_refresh_token(employee.id)

    await AuditService(db).log(
        action="auth.login",
        entity_type="employee",
        entity_id=str(employee.id),
        actor=employee,
        request=request,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_access_token(body: RefreshRequest, db: DbSession):
    """
    Exchange a valid refresh token for a new access token.
    The refresh token itself is NOT rotated here (add rotation in Phase 6 if needed).
    """
    employee_id_str = verify_refresh_token(body.refresh_token)
    if not employee_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    result = await db.execute(
        select(Employee).where(
            Employee.id == employee_id_str,
            Employee.is_active == True,   # noqa: E712
        )
    )
    employee = result.scalar_one_or_none()
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account not found or deactivated",
        )

    return AccessTokenResponse(
        access_token=create_access_token(employee.id, employee.role.value)
    )


@router.get("/me", response_model=MeResponse)
async def get_me(current_user: CurrentUser):
    """Return the authenticated user's own profile."""
    return MeResponse(
        id=str(current_user.id),
        employee_code=current_user.employee_code,
        full_name=current_user.full_name,
        email=current_user.email,
        role=current_user.role.value,
        department_name=(
            current_user.department.name if current_user.department else None
        ),
        is_enrolled=current_user.is_enrolled,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout():
    """
    JWT is stateless — we can't truly invalidate a token server-side here.
    The client should delete both tokens from storage on logout.

    Phase 6: add a token blocklist in Redis if true server-side invalidation is needed.
    """
    return None
