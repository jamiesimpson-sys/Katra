import enum
import uuid
from datetime import datetime

from sqlalchemy import ARRAY, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from katra.models.base import Base, CreatedAtMixin, IdMixin, str_enum


class InterviewStatus(enum.StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"


class Speaker(enum.StrEnum):
    INTERVIEWER = "interviewer"
    OWNER = "owner"


class CoverageStatus(enum.StrEnum):
    UNASKED = "unasked"
    ASKED = "asked"
    PARTIAL = "partial"
    ANSWERED = "answered"


class InterviewSession(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "interview_sessions"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    status: Mapped[InterviewStatus] = mapped_column(
        str_enum(InterviewStatus, "interview_status"), default=InterviewStatus.ACTIVE
    )
    current_question_id: Mapped[str | None] = mapped_column(String(100))
    started_at: Mapped[datetime | None]
    ended_at: Mapped[datetime | None]


class SessionTurn(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "session_turns"
    __table_args__ = (UniqueConstraint("session_id", "ordinal"),)

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="CASCADE"), index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer)
    speaker: Mapped[Speaker] = mapped_column(str_enum(Speaker, "speaker"))
    text: Mapped[str] = mapped_column(Text)
    question_id: Mapped[str | None] = mapped_column(String(100))
    referenced_chunk_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(Uuid), default=list)


class QuestionCoverage(Base):
    __tablename__ = "question_coverage"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    question_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    status: Mapped[CoverageStatus] = mapped_column(
        str_enum(CoverageStatus, "coverage_status"), default=CoverageStatus.UNASKED
    )
    last_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="SET NULL")
    )
