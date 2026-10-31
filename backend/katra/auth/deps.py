"""Authentication and authorization dependencies.

Every route under /api/projects/{project_id} must depend on `require_project_role`;
tests/test_route_inventory.py enforces this.
"""

import secrets
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from katra.auth.sessions import find_session
from katra.config import get_settings
from katra.db.session import get_db
from katra.models import AuthSession, Project, ProjectMember, Role, User

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

DbSession = Annotated[Session, Depends(get_db)]


@dataclass
class CurrentUser:
    user: User
    session: AuthSession

    @property
    def id(self) -> uuid.UUID:
        return self.user.id


@dataclass
class ProjectContext:
    """Proof that `user` is a member of `project` with `role`. Services take this, not ids."""

    project: Project
    user: User
    role: Role

    @property
    def project_id(self) -> uuid.UUID:
        return self.project.id


def get_current_user(request: Request, db: DbSession) -> CurrentUser:
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    session = find_session(db, token) if token else None
    if session is None or not session.user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")
    if request.method not in SAFE_METHODS:
        sent = request.headers.get("X-CSRF-Token", "")
        if not secrets.compare_digest(sent, session.csrf_token):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Missing or invalid CSRF token")
    return CurrentUser(user=session.user, session=session)


AuthedUser = Annotated[CurrentUser, Depends(get_current_user)]


def require_staff(current: AuthedUser) -> CurrentUser:
    if not current.user.is_staff:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Staff only")
    return current


StaffUser = Annotated[CurrentUser, Depends(require_staff)]


def require_project_role(*roles: Role) -> Callable[..., ProjectContext]:
    """Dependency factory: the caller must be a project member with one of `roles`.

    Non-members get 404 so project ids can't be probed.
    """
    allowed = set(roles) or set(Role)

    def dependency(project_id: uuid.UUID, current: AuthedUser, db: DbSession) -> ProjectContext:
        row = db.execute(
            select(Project, ProjectMember.role)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(Project.id == project_id, ProjectMember.user_id == current.user.id)
        ).first()
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
        project, role = row
        if role not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed for your role")
        return ProjectContext(project=project, user=current.user, role=role)

    dependency.__katra_rbac__ = True  # type: ignore[attr-defined]
    return dependency


AnyMember = Annotated[ProjectContext, Depends(require_project_role())]
AdminOnly = Annotated[ProjectContext, Depends(require_project_role(Role.ADMIN))]
