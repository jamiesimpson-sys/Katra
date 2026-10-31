import enum
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from katra.models.base import EMBEDDING_DIM, Base, CreatedAtMixin, IdMixin, str_enum


class ItemStatus(enum.StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    EDITED = "edited"  # owner rewrote the claim and approved it: counts as verified
    REJECTED = "rejected"


VERIFIED_STATUSES = (ItemStatus.APPROVED, ItemStatus.EDITED)


class FlagStatus(enum.StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class KnowledgeItem(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "knowledge_items"
    __table_args__ = (
        Index(
            "ix_knowledge_items_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    section_id: Mapped[str] = mapped_column(String(100))
    question_id: Mapped[str | None] = mapped_column(String(100))
    claim: Mapped[str] = mapped_column(Text)
    original_claim: Mapped[str] = mapped_column(Text)
    # The exact owner words this claim rests on, and where they are in the transcript.
    quote: Mapped[str] = mapped_column(Text)
    turn_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("session_turns.id", ondelete="CASCADE"))
    quote_start: Mapped[int] = mapped_column(Integer)
    quote_end: Mapped[int] = mapped_column(Integer)
    status: Mapped[ItemStatus] = mapped_column(
        str_enum(ItemStatus, "item_status"), default=ItemStatus.DRAFT
    )
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    verified_at: Mapped[datetime | None]
    prompt_version: Mapped[str | None] = mapped_column(String(50))
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))


class KnowledgeItemChunk(Base):
    __tablename__ = "knowledge_item_chunks"

    knowledge_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_items.id", ondelete="CASCADE"), primary_key=True
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_chunks.id", ondelete="CASCADE"), primary_key=True
    )


class ContradictionFlag(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "contradiction_flags"
    __table_args__ = (
        CheckConstraint(
            "(other_item_id IS NOT NULL) <> (chunk_id IS NOT NULL)", name="one_counterpart"
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_items.id", ondelete="CASCADE"))
    other_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("knowledge_items.id", ondelete="CASCADE")
    )
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("document_chunks.id", ondelete="CASCADE")
    )
    explanation: Mapped[str] = mapped_column(Text)
    status: Mapped[FlagStatus] = mapped_column(
        str_enum(FlagStatus, "flag_status"), default=FlagStatus.OPEN
    )
    resolution_note: Mapped[str | None] = mapped_column(Text)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    resolved_at: Mapped[datetime | None]
