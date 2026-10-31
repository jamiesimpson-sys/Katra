"""Public invite endpoints: the raw token in the URL is the credential."""

from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import func, select

from katra.auth.deps import DbSession
from katra.auth.security import hash_password, verify_password
from katra.auth.sessions import start_session
from katra.models import Project, ProjectMember, User
from katra.models.base import utcnow
from katra.schemas.common import InviteAcceptIn, InvitePreview, MeOut, UserOut
from katra.services import audit
from katra.services.invites import find_open_invite

router = APIRouter(prefix="/api/invites", tags=["invites"])

INVALID = "This invite link is invalid or has expired"


def _user_by_email(db: DbSession, email: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.email) == email.lower()))


@router.get("/{token}", response_model=InvitePreview)
def preview_invite(token: str, db: DbSession) -> InvitePreview:
    invite = find_open_invite(db, token)
    if invite is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, INVALID)
    project = db.get(Project, invite.project_id)
    assert project is not None
    return InvitePreview(
        project_name=project.name,
        email=invite.email,
        role=invite.role,
        user_exists=_user_by_email(db, invite.email) is not None,
    )


@router.post("/{token}/accept", response_model=MeOut)
def accept_invite(
    token: str, body: InviteAcceptIn, request: Request, response: Response, db: DbSession
) -> MeOut:
    invite = find_open_invite(db, token)
    if invite is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, INVALID)

    user = _user_by_email(db, invite.email)
    if user is None:
        user = User(
            email=invite.email,
            display_name=body.display_name.strip(),
            password_hash=hash_password(body.password),
        )
        db.add(user)
        db.flush()
    elif not verify_password(user.password_hash, body.password):
        # Existing account: the password proves it's theirs.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong password for this account")

    if db.get(ProjectMember, (invite.project_id, user.id)) is None:
        db.add(ProjectMember(project_id=invite.project_id, user_id=user.id, role=invite.role))
    invite.accepted_at = utcnow()
    issued = start_session(db, user, response)
    audit.record(
        db,
        "invite.accept",
        user_id=user.id,
        project_id=invite.project_id,
        target_type="invite",
        target_id=invite.id,
        details={"role": invite.role.value},
        request=request,
    )
    db.commit()
    return MeOut(user=UserOut.model_validate(user), csrf_token=issued.csrf_token)
