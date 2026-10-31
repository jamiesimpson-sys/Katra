from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import func, select

from katra.auth.deps import AuthedUser, DbSession
from katra.auth.ratelimit import SlidingWindowLimiter
from katra.auth.security import DUMMY_HASH, verify_password
from katra.auth.sessions import end_session, start_session
from katra.config import get_settings
from katra.models import User
from katra.schemas.common import LoginIn, MeOut, UserOut
from katra.services import audit

router = APIRouter(prefix="/api/auth", tags=["auth"])

_settings = get_settings()
login_limiter = SlidingWindowLimiter(_settings.login_max_attempts, _settings.login_window_seconds)


@router.post("/login", response_model=MeOut)
def login(body: LoginIn, request: Request, response: Response, db: DbSession) -> MeOut:
    email = body.email.lower()
    ip = request.client.host if request.client else "unknown"
    if not login_limiter.hit(f"{ip}:{email}"):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts, try later")

    user = db.scalar(select(User).where(func.lower(User.email) == email))
    ok = verify_password(user.password_hash if user else DUMMY_HASH, body.password)
    if not user or not ok or not user.is_active:
        audit.record(db, "auth.login_failed", user_id=user.id if user else None, request=request)
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    issued = start_session(db, user, response)
    audit.record(db, "auth.login", user_id=user.id, request=request)
    db.commit()
    return MeOut(user=UserOut.model_validate(user), csrf_token=issued.csrf_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(current: AuthedUser, request: Request, response: Response, db: DbSession) -> None:
    end_session(db, current.session, response)
    audit.record(db, "auth.logout", user_id=current.id, request=request)
    db.commit()


@router.get("/me", response_model=MeOut)
def me(current: AuthedUser) -> MeOut:
    return MeOut(user=UserOut.model_validate(current.user), csrf_token=current.session.csrf_token)
