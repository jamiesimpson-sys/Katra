"""All models are imported here so Alembic and the app see the full schema."""

from katra.models.audit import AuditLog
from katra.models.base import EMBEDDING_DIM, Base
from katra.models.documents import Document, DocumentChunk, DocumentStatus
from katra.models.identity import AuthSession, Invite, ProjectMember, Role, User
from katra.models.interviews import (
    CoverageStatus,
    InterviewSession,
    InterviewStatus,
    QuestionCoverage,
    SessionTurn,
    Speaker,
)
from katra.models.jobs import Job, JobStatus
from katra.models.knowledge import (
    VERIFIED_STATUSES,
    ContradictionFlag,
    FlagStatus,
    ItemStatus,
    KnowledgeItem,
    KnowledgeItemChunk,
)
from katra.models.outputs import QAMessage, Report
from katra.models.project import Project, ProjectKey, ProjectStatus

__all__ = [
    "EMBEDDING_DIM",
    "VERIFIED_STATUSES",
    "AuditLog",
    "AuthSession",
    "Base",
    "ContradictionFlag",
    "CoverageStatus",
    "Document",
    "DocumentChunk",
    "DocumentStatus",
    "FlagStatus",
    "InterviewSession",
    "InterviewStatus",
    "Invite",
    "ItemStatus",
    "Job",
    "JobStatus",
    "KnowledgeItem",
    "KnowledgeItemChunk",
    "Project",
    "ProjectKey",
    "ProjectMember",
    "ProjectStatus",
    "QAMessage",
    "QuestionCoverage",
    "Report",
    "Role",
    "SessionTurn",
    "Speaker",
    "User",
]
