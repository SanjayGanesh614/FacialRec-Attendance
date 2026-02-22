# app/api/v1/endpoints/devices.py
# ─────────────────────────────────────────────────────────────
# Endpoints called by Pi devices (device key auth only).
#
# The Pi calls:
#   GET  /devices/pending-enrollment  — check if anyone needs enrolling
#   POST /devices/enrollment-complete — Pi confirms enrollment done
#   GET  /devices/embeddings/sync     — download updated embedding DB
#   POST /devices/unknown-face        — report an unrecognised face event
# ─────────────────────────────────────────────────────────────

from fastapi import APIRouter, UploadFile, File, Form
from sqlalchemy import select

from app.core.dependencies import DbSession, DeviceAuth
from app.models.employee import Employee
from app.services.audit_service import AuditService

router = APIRouter(prefix="/devices", tags=["Devices (Pi)"])


@router.get("/pending-enrollment")
async def get_pending_enrollments(db: DbSession, _: DeviceAuth):
    """
    Pi polls this endpoint to check if any employees need face enrollment.
    Returns list of employees with enrollment_pending=True.

    Pi behaviour on receiving a pending employee:
      1. Enter enrollment mode for that person
      2. Capture photos, run pipeline, save embeddings locally
      3. Call /devices/enrollment-complete to confirm
    """
    result = await db.execute(
        select(Employee).where(
            Employee.enrollment_pending == True,  # noqa: E712
            Employee.is_active == True,           # noqa: E712
        )
    )
    pending = result.scalars().all()

    return {
        "pending": [
            {
                "employee_id": emp.employee_code,
                "employee_db_id": str(emp.id),
                "name": emp.full_name,
                "notes": emp.enrollment_notes,
            }
            for emp in pending
        ],
        "count": len(pending),
    }


@router.post("/enrollment-complete")
async def confirm_enrollment(
    employee_code: str = Form(...),
    device_id: str = Form(...),
    samples_captured: int = Form(...),
    db: DbSession = None,
    _: DeviceAuth = None,
):
    """
    Pi calls this after successfully capturing face embeddings for an employee.
    Updates the employee record: is_enrolled=True, enrollment_pending=False.
    """
    result = await db.execute(
        select(Employee).where(Employee.employee_code == employee_code)
    )
    employee = result.scalar_one_or_none()

    if not employee:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Employee not found")

    employee.is_enrolled = True
    employee.enrollment_pending = False

    await AuditService(db).log(
        action="employee.enrollment_complete",
        entity_type="employee",
        entity_id=str(employee.id),
        new_value={
            "device_id": device_id,
            "samples_captured": samples_captured,
        },
        notes=f"Face enrollment confirmed via device {device_id}",
    )

    return {
        "success": True,
        "message": f"Enrollment confirmed for {employee.full_name}",
    }


@router.post("/unknown-face")
async def report_unknown_face(
    device_id: str = Form(...),
    timestamp: str = Form(...),
    liveness_score: float = Form(default=1.0),
    db: DbSession = None,
    _: DeviceAuth = None,
):
    """
    Pi reports an unrecognised face event.
    In Phase 5 this will notify the admin via email/push.
    For now we log it to the audit trail.
    """
    await AuditService(db).log(
        action="attendance.unknown_face",
        entity_type="device",
        entity_id=device_id,
        new_value={
            "device_id": device_id,
            "timestamp": timestamp,
            "liveness_score": liveness_score,
        },
        notes="Unrecognised face detected",
    )
    return {"received": True}
