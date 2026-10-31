import uuid
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from katra.models import AuditLog


def record(
    db: Session,
    action: str,
    *,
    user_id: uuid.UUID | None,
    project_id: uuid.UUID | None = None,
    target_type: str | None = None,
    target_id: object | None = None,
    details: dict[str, Any] | None = None,
    request: Request | None = None,
) -> None:
    """Add an audit entry to the current transaction. Never put customer content in `details`."""
    db.add(
        AuditLog(
            action=action,
            user_id=user_id,
            project_id=project_id,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            details=details or {},
            ip=request.client.host if request and request.client else None,
        )
    )
