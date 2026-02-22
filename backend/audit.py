# app/models/audit.py
# ─────────────────────────────────────────────────────────────
# Immutable audit log.
# Every write action in the system is recorded here:
#   who did what, to which entity, when, from where.
# Never delete from this table.
# ─────────────────────────────────────────────────────────────

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET

from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Who performed the action (null = system / automated job)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actor_name: Mapped[str | None] = mapped_column(String(150), nullable=True)

    # What happened — verb style: "employee.create", "attendance.correct", etc.
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Which type of entity was affected
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # The UUID of the affected record
    entity_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Snapshots of the record before and after — JSONB for flexible storage
    old_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Extra context (e.g. "reason: new hire")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Network context
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} on {self.entity_type}:{self.entity_id} by {self.actor_id}>"
