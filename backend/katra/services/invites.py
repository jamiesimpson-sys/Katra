from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from katra.auth.deps import ProjectContext
from katra.auth.security import hash_token, new_token
from katra.config import get_settings
from katra.models import Invite, Role
from katra.models.base import utcnow


def create_invite(db: Session, ctx: ProjectContext, email: str, role: Role) -> tuple[Invite, str]:
    """Returns the invite and its raw token. Only the hash is stored."""
    settings = get_settings()
    token = new_token()
    invite = Invite(
        project_id=ctx.project_id,
        email=email.lower(),
        role=role,
        token_hash=hash_token(token),
        invited_by=ctx.user.id,
        expires_at=utcnow() + timedelta(hours=settings.invite_ttl_hours),
    )
    db.add(invite)
    db.flush()
    return invite, token


def invite_url(token: str) -> str:
    return f"{get_settings().public_base_url.rstrip('/')}/invite/{token}"


def find_open_invite(db: Session, token: str) -> Invite | None:
    invite = db.scalar(select(Invite).where(Invite.token_hash == hash_token(token)))
    if (
        invite is None
        or invite.accepted_at is not None
        or invite.revoked_at is not None
        or invite.expires_at <= utcnow()
    ):
        return None
    return invite
