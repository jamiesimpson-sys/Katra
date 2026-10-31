from dataclasses import dataclass
from datetime import timedelta

from fastapi import Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from katra.auth.security import hash_token, new_token
from katra.config import get_settings
from katra.models import AuthSession, User
from katra.models.base import utcnow


@dataclass
class IssuedSession:
    token: str
    csrf_token: str


def start_session(db: Session, user: User, response: Response) -> IssuedSession:
    settings = get_settings()
    token, csrf = new_token(), new_token()
    ttl = timedelta(hours=settings.session_ttl_hours)
    db.add(
        AuthSession(
            user_id=user.id,
            token_hash=hash_token(token),
            csrf_token=csrf,
            expires_at=utcnow() + ttl,
        )
    )
    # Opportunistic cleanup of this user's expired sessions.
    db.execute(
        delete(AuthSession).where(AuthSession.user_id == user.id, AuthSession.expires_at < utcnow())
    )
    max_age = int(ttl.total_seconds())
    response.set_cookie(
        settings.session_cookie_name,
        token,
        max_age=max_age,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    # Readable by the SPA, which echoes it in the X-CSRF-Token header (double submit).
    response.set_cookie(
        settings.csrf_cookie_name,
        csrf,
        max_age=max_age,
        httponly=False,
        secure=True,
        samesite="lax",
        path="/",
    )
    return IssuedSession(token=token, csrf_token=csrf)


def find_session(db: Session, token: str) -> AuthSession | None:
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == hash_token(token)))
    if session is None or session.expires_at <= utcnow():
        return None
    return session


def end_session(db: Session, session: AuthSession, response: Response) -> None:
    settings = get_settings()
    db.delete(session)
    response.delete_cookie(settings.session_cookie_name, path="/", secure=True, httponly=True)
    response.delete_cookie(settings.csrf_cookie_name, path="/", secure=True)
