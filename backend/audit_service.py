# app/services/audit_service.py
# ─────────────────────────────────────────────────────────────
# Write audit log entries from anywhere in the app.
# Usage:
#   await AuditService(db).log(
#       actor=current_user,
#       action="employee.create",
#       entity_type="employee",
#       entity_id=str(new_employee.id),
#       new_value={"name": new_employee.full_name},
#       request=request,   # FastAPI Request for IP extraction
#   )
# ─────────────────────────────────────────────────────────────

from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.employee import Employee


class AuditService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        action: str,
        entity_type: str,
        entity_id: str | None = None,
        actor: Employee | None = None,
        old_value: dict | None = None,
        new_value: dict | None = None,
        notes: str | None = None,
        request: Request | None = None,
    ) -> None:
        """
        Write one audit log entry.
        This is a fire-and-forget within the current transaction —
        if the outer transaction rolls back, this entry is also rolled back
        (which is what we want — don't log changes that didn't happen).
        """
        ip = None
        if request:
            # X-Forwarded-For handles reverse proxy deployments
            forwarded = request.headers.get("X-Forwarded-For")
            ip = forwarded.split(",")[0].strip() if forwarded else str(request.client.host)

        entry = AuditLog(
            actor_id=actor.id if actor else None,
            actor_name=actor.full_name if actor else "system",
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=old_value,
            new_value=new_value,
            notes=notes,
            ip_address=ip,
        )
        self.db.add(entry)
        # No flush here — let the route's commit handle it
