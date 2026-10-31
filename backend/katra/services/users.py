from sqlalchemy import func, select
from sqlalchemy.orm import Session

from katra.auth.security import MIN_PASSWORD_LENGTH, hash_password
from katra.models import User


def create_staff_user(db: Session, email: str, password: str, display_name: str = "") -> User:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    if db.scalar(select(User).where(func.lower(User.email) == email.lower())):
        raise ValueError(f"A user with email {email} already exists")
    user = User(
        email=email.lower(),
        display_name=display_name,
        password_hash=hash_password(password),
        is_staff=True,
    )
    db.add(user)
    db.flush()
    return user


def bootstrap_admin(db: Session, email: str | None, password: str | None) -> User | None:
    """Create the first staff user from env vars if the database has no users yet."""
    if not email or not password:
        return None
    if db.scalar(select(func.count()).select_from(User)):
        return None
    user = create_staff_user(db, email, password, display_name="Admin")
    db.commit()
    return user
