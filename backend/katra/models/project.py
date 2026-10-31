import enum
import uuid
from typing import Any

from sqlalchemy import ForeignKey, Integer, LargeBinary, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from katra.models.base import Base, CreatedAtMixin, IdMixin, str_enum


class ProjectStatus(enum.StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class Project(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(200))
    module_id: Mapped[str] = mapped_column(String(100))
    module_version: Mapped[int] = mapped_column(Integer, default=1)
    # Copy of the module definition taken at creation, so later edits to the module file
    # never change an in-flight project.
    module_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    status: Mapped[ProjectStatus] = mapped_column(
        str_enum(ProjectStatus, "project_status"), default=ProjectStatus.ACTIVE
    )
    # None = keep until deleted by an admin.
    retention_days: Mapped[int | None] = mapped_column(Integer)


class ProjectKey(CreatedAtMixin, Base):
    """Per-project data key, wrapped by the master key. Deleting it crypto-shreds the blobs."""

    __tablename__ = "project_keys"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    wrapped_dek: Mapped[bytes] = mapped_column(LargeBinary)
