import uuid

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from katra.auth.deps import AdminOnly, AnyMember, AuthedUser, DbSession, StaffUser
from katra.engine.modules import Module, get_registry
from katra.models import AuditLog, Invite, Project, ProjectMember, Role, User
from katra.models.base import utcnow
from katra.schemas.common import (
    AuditOut,
    InviteCreated,
    InviteIn,
    InviteOut,
    MemberOut,
    ProjectIn,
    ProjectOut,
    ProjectWithRole,
    UserOut,
)
from katra.services import audit
from katra.services.invites import create_invite, invite_url
from katra.services.modules import module_for_project

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[ProjectWithRole])
def list_projects(current: AuthedUser, db: DbSession) -> list[ProjectWithRole]:
    rows = db.execute(
        select(Project, ProjectMember.role)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(ProjectMember.user_id == current.id)
        .order_by(Project.created_at.desc())
    ).all()
    return [
        ProjectWithRole(**ProjectOut.model_validate(p).model_dump(), role=role) for p, role in rows
    ]


@router.post("", response_model=ProjectWithRole, status_code=status.HTTP_201_CREATED)
def create_project(
    body: ProjectIn, current: StaffUser, request: Request, db: DbSession
) -> ProjectWithRole:
    module = get_registry().get(body.module_id)
    if module is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown module")
    project = Project(
        name=body.name,
        module_id=module.id,
        module_version=module.version,
        module_snapshot=module.model_dump(mode="json"),
        retention_days=body.retention_days,
    )
    db.add(project)
    db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=current.id, role=Role.ADMIN))
    audit.record(
        db,
        "project.create",
        user_id=current.id,
        project_id=project.id,
        target_type="project",
        target_id=project.id,
        details={"module_id": module.id, "module_version": module.version},
        request=request,
    )
    db.commit()
    return ProjectWithRole(**ProjectOut.model_validate(project).model_dump(), role=Role.ADMIN)


@router.get("/{project_id}", response_model=ProjectWithRole)
def get_project(ctx: AnyMember, request: Request, db: DbSession) -> ProjectWithRole:
    audit.record(
        db,
        "project.view",
        user_id=ctx.user.id,
        project_id=ctx.project_id,
        target_type="project",
        target_id=ctx.project_id,
        request=request,
    )
    db.commit()
    return ProjectWithRole(**ProjectOut.model_validate(ctx.project).model_dump(), role=ctx.role)


@router.get("/{project_id}/module", response_model=Module)
def get_project_module(ctx: AnyMember) -> Module:
    """The question bank and rules this project runs on (read-only)."""
    return module_for_project(ctx.project)


@router.get("/{project_id}/members", response_model=list[MemberOut])
def list_members(ctx: AdminOnly, db: DbSession) -> list[MemberOut]:
    rows = db.scalars(
        select(ProjectMember)
        .where(ProjectMember.project_id == ctx.project_id)
        .order_by(ProjectMember.created_at)
    ).all()
    return [
        MemberOut(user=UserOut.model_validate(m.user), role=m.role, created_at=m.created_at)
        for m in rows
    ]


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(ctx: AdminOnly, user_id: uuid.UUID, request: Request, db: DbSession) -> None:
    if user_id == ctx.user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You can't remove yourself")
    member = db.get(ProjectMember, (ctx.project_id, user_id))
    if member is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    db.delete(member)
    audit.record(
        db,
        "member.remove",
        user_id=ctx.user.id,
        project_id=ctx.project_id,
        target_type="user",
        target_id=user_id,
        request=request,
    )
    db.commit()


@router.get("/{project_id}/invites", response_model=list[InviteOut])
def list_invites(ctx: AdminOnly, db: DbSession) -> list[Invite]:
    return list(
        db.scalars(
            select(Invite)
            .where(Invite.project_id == ctx.project_id)
            .order_by(Invite.created_at.desc())
        )
    )


@router.post(
    "/{project_id}/invites", response_model=InviteCreated, status_code=status.HTTP_201_CREATED
)
def invite_member(body: InviteIn, ctx: AdminOnly, request: Request, db: DbSession) -> InviteCreated:
    existing = db.scalar(
        select(ProjectMember)
        .join(User, User.id == ProjectMember.user_id)
        .where(ProjectMember.project_id == ctx.project_id, User.email == body.email.lower())
    )
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Already a member of this project")
    invite, token = create_invite(db, ctx, body.email, body.role)
    audit.record(
        db,
        "invite.create",
        user_id=ctx.user.id,
        project_id=ctx.project_id,
        target_type="invite",
        target_id=invite.id,
        details={"role": body.role.value},
        request=request,
    )
    db.commit()
    return InviteCreated(
        **InviteOut.model_validate(invite).model_dump(), invite_url=invite_url(token, request)
    )


@router.delete("/{project_id}/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_invite(ctx: AdminOnly, invite_id: uuid.UUID, request: Request, db: DbSession) -> None:
    invite = db.scalar(
        select(Invite).where(Invite.id == invite_id, Invite.project_id == ctx.project_id)
    )
    if invite is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invite not found")
    if invite.accepted_at is None and invite.revoked_at is None:
        invite.revoked_at = utcnow()
    audit.record(
        db,
        "invite.revoke",
        user_id=ctx.user.id,
        project_id=ctx.project_id,
        target_type="invite",
        target_id=invite.id,
        request=request,
    )
    db.commit()


@router.get("/{project_id}/audit", response_model=list[AuditOut])
def list_audit(ctx: AdminOnly, db: DbSession, limit: int = 200) -> list[AuditLog]:
    return list(
        db.scalars(
            select(AuditLog)
            .where(AuditLog.project_id == ctx.project_id)
            .order_by(AuditLog.created_at.desc())
            .limit(min(max(limit, 1), 1000))
        )
    )
