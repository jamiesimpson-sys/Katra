import uuid
from typing import Any

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from katra.models.base import Base, CreatedAtMixin, IdMixin


class Report(IdMixin, CreatedAtMixin, Base):
    """Immutable: regenerating a report creates a new row."""

    __tablename__ = "reports"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    output_id: Mapped[str] = mapped_column(String(100))
    content_md: Mapped[str] = mapped_column(Text)
    citations: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    coverage_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    generated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )


class QAMessage(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "qa_messages"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    citations: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    refused: Mapped[bool] = mapped_column(Boolean, default=False)
