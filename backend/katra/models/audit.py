import uuid
from typing import Any

from sqlalchemy import String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from katra.models.base import Base, CreatedAtMixin, IdMixin


class AuditLog(IdMixin, CreatedAtMixin, Base):
    """Append-only (enforced by a trigger). Holds ids and actions, never content.

    No foreign keys, so entries outlive the users and projects they refer to.
    """

    __tablename__ = "audit_log"

    project_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    action: Mapped[str] = mapped_column(String(100))
    target_type: Mapped[str | None] = mapped_column(String(100))
    target_id: Mapped[str | None] = mapped_column(String(100))
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    ip: Mapped[str | None] = mapped_column(String(64))
