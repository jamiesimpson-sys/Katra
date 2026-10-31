"""Superuser data browser at /admin (SQLAdmin).

Read-only by default. A few safe fields can be edited (see the views below). Anything
that would bypass the app's rules (owner verification, the audit log, secrets) is
read-only or hidden. Every page view and change is written to the audit log.
"""

import secrets

from fastapi import FastAPI
from sqladmin import Admin, ModelView
from sqladmin.audit import AuditBackend, AuditEntry
from sqladmin.authentication import AuthenticationBackend, get_current_user_id
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import PlainTextResponse, RedirectResponse, Response

from katra.auth.sessions import end_session, find_session
from katra.config import get_settings
from katra.db.session import get_engine, get_sessionmaker
from katra.models import (
    AuditLog,
    ContradictionFlag,
    Document,
    DocumentChunk,
    InterviewSession,
    Invite,
    Job,
    KnowledgeItem,
    Project,
    ProjectMember,
    QAMessage,
    Report,
    SessionTurn,
    User,
)
from katra.services import audit

# Never shown, in lists or detail pages. Each view hides its own (tests check every view);
# tables holding nothing but secrets (auth sessions, project keys) have no view at all.
SECRET_COLUMNS = {"password_hash", "token_hash", "csrf_token", "wrapped_dek", "embedding"}


class SuperuserAuth(AuthenticationBackend):
    """Reuses the normal Katra session cookie; only active superusers get in."""

    def __init__(self) -> None:
        # SQLAdmin requires a session secret, but we don't use its session.
        super().__init__(secret_key=secrets.token_urlsafe(32))

    async def login(self, request: Request) -> Response:
        return RedirectResponse("/login", status_code=302)

    async def logout(self, request: Request) -> Response:
        response = RedirectResponse("/login", status_code=302)
        token = request.cookies.get(get_settings().session_cookie_name)
        await run_in_threadpool(_end_session, token, response)
        return response

    async def authenticate(self, request: Request) -> Response | bool:
        token = request.cookies.get(get_settings().session_cookie_name)
        result = await run_in_threadpool(_check_and_audit, token, request)
        if result == "anonymous":
            return RedirectResponse("/login", status_code=302)
        if result == "forbidden":
            return PlainTextResponse("Superusers only", status_code=403)
        request.state.katra_user_id = result
        return True

    async def get_user_id(self, request: Request) -> object:
        return getattr(request.state, "katra_user_id", None)


def _end_session(token: str | None, response: Response) -> None:
    with get_sessionmaker()() as db:
        session = find_session(db, token) if token else None
        if session is not None:
            audit.record(db, "auth.logout", user_id=session.user_id)
            end_session(db, session, response)
            db.commit()


def _check_and_audit(token: str | None, request: Request) -> str:
    with get_sessionmaker()() as db:
        session = find_session(db, token) if token else None
        if session is None or not session.user.is_active:
            return "anonymous"
        if not session.user.is_superuser:
            return "forbidden"
        if request.method == "GET":
            audit.record(
                db,
                "admin.view",
                user_id=session.user.id,
                details={"path": request.url.path},
                request=request,
            )
            db.commit()
        return session.user.id


class KatraAuditBackend(AuditBackend):
    """Records admin edits in audit_log: which fields changed, never their values."""

    async def log(self, entry: AuditEntry, request: Request) -> None:
        user_id = get_current_user_id(request)

        def write() -> None:
            with get_sessionmaker()() as db:
                audit.record(
                    db,
                    f"admin.{entry.action}",
                    user_id=user_id,
                    project_id=entry.pk if entry.identity == "project" else None,
                    target_type=entry.identity,
                    target_id=entry.pk,
                    details={"fields": sorted(entry.changes or {})},
                    request=request,
                )
                db.commit()

        await run_in_threadpool(write)


class ReadOnlyView(ModelView):
    can_create = False
    can_edit = False
    can_delete = False
    can_export = False
    can_view_details = True
    page_size = 50


# --- Editable (safe fields only) ----------------------------------------------------


class UserAdmin(ReadOnlyView, model=User):
    name_plural = "Users"
    icon = "fa-solid fa-user"
    can_edit = True
    form_columns = [User.display_name, User.is_active, User.is_staff]
    column_exclude_list = column_details_exclude_list = [User.password_hash]
    column_searchable_list = [User.email]
    column_default_sort = [(User.created_at, True)]


class ProjectAdmin(ReadOnlyView, model=Project):
    name_plural = "Projects"
    icon = "fa-solid fa-folder"
    can_edit = True
    form_columns = [Project.name, Project.status, Project.retention_days]
    column_list = [
        Project.id,
        Project.name,
        Project.module_id,
        Project.module_version,
        Project.status,
        Project.created_at,
    ]
    column_details_exclude_list = [Project.module_snapshot]  # long; shown in the app instead
    column_searchable_list = [Project.name]
    column_default_sort = [(Project.created_at, True)]


class InviteAdmin(ReadOnlyView, model=Invite):
    name_plural = "Invites"
    icon = "fa-solid fa-envelope"
    can_edit = True
    form_columns = [Invite.revoked_at]  # set a time to revoke
    column_exclude_list = column_details_exclude_list = [Invite.token_hash]
    column_searchable_list = [Invite.email]
    column_default_sort = [(Invite.created_at, True)]


# --- Read-only ----------------------------------------------------------------------


class MemberAdmin(ReadOnlyView, model=ProjectMember):
    name_plural = "Project members"
    icon = "fa-solid fa-users"


class DocumentAdmin(ReadOnlyView, model=Document):
    name_plural = "Documents"
    icon = "fa-solid fa-file"
    column_list = [Document.filename, Document.project_id, Document.status, Document.created_at]


class ChunkAdmin(ReadOnlyView, model=DocumentChunk):
    name_plural = "Document chunks"
    icon = "fa-solid fa-puzzle-piece"
    column_exclude_list = column_details_exclude_list = [DocumentChunk.embedding]


class InterviewAdmin(ReadOnlyView, model=InterviewSession):
    name_plural = "Interview sessions"
    icon = "fa-solid fa-comments"


class TurnAdmin(ReadOnlyView, model=SessionTurn):
    name_plural = "Interview turns"
    icon = "fa-solid fa-comment"


class KnowledgeAdmin(ReadOnlyView, model=KnowledgeItem):
    """Read-only: changing answers or their status here would bypass owner verification."""

    name_plural = "Knowledge items"
    icon = "fa-solid fa-lightbulb"
    column_exclude_list = column_details_exclude_list = [KnowledgeItem.embedding]


class FlagAdmin(ReadOnlyView, model=ContradictionFlag):
    name_plural = "Contradiction flags"
    icon = "fa-solid fa-triangle-exclamation"


class ReportAdmin(ReadOnlyView, model=Report):
    name_plural = "Reports"
    icon = "fa-solid fa-file-lines"


class QAAdmin(ReadOnlyView, model=QAMessage):
    name_plural = "Q&A messages"
    icon = "fa-solid fa-circle-question"


class AuditAdmin(ReadOnlyView, model=AuditLog):
    name_plural = "Audit log"
    icon = "fa-solid fa-clipboard-list"
    column_default_sort = [(AuditLog.created_at, True)]
    column_searchable_list = [AuditLog.action]


class JobAdmin(ReadOnlyView, model=Job):
    name_plural = "Jobs"
    icon = "fa-solid fa-gears"
    column_default_sort = [(Job.created_at, True)]


VIEWS: list[type[ModelView]] = [
    UserAdmin,
    ProjectAdmin,
    MemberAdmin,
    InviteAdmin,
    DocumentAdmin,
    ChunkAdmin,
    InterviewAdmin,
    TurnAdmin,
    KnowledgeAdmin,
    FlagAdmin,
    ReportAdmin,
    QAAdmin,
    AuditAdmin,
    JobAdmin,
]


def mount_admin(app: FastAPI) -> Admin:
    admin = Admin(
        app,
        engine=get_engine(),
        session_maker=get_sessionmaker(),
        base_url="/admin",
        title="Katra admin",
        authentication_backend=SuperuserAuth(),
        audit_backend=KatraAuditBackend(),
    )
    for view in VIEWS:
        admin.add_view(view)
    return admin
