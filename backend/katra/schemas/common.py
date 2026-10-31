import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from katra.auth.security import MIN_PASSWORD_LENGTH
from katra.models import ProjectStatus, Role


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserOut(ORMModel):
    id: uuid.UUID
    email: str
    display_name: str
    is_staff: bool


class LoginIn(BaseModel):
    # Plain string: login only compares against stored emails.
    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=1000)


class MeOut(BaseModel):
    user: UserOut
    csrf_token: str


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    module_id: str = Field(min_length=1, max_length=100)
    retention_days: int | None = Field(default=None, ge=1, le=3650)


class ProjectOut(ORMModel):
    id: uuid.UUID
    name: str
    module_id: str
    module_version: int
    status: ProjectStatus
    retention_days: int | None
    created_at: datetime


class ProjectWithRole(ProjectOut):
    role: Role


class MemberOut(BaseModel):
    user: UserOut
    role: Role
    created_at: datetime


class InviteIn(BaseModel):
    email: EmailStr
    role: Role


class InviteOut(ORMModel):
    id: uuid.UUID
    email: str
    role: Role
    expires_at: datetime
    accepted_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


class InviteCreated(InviteOut):
    # Shown once to the admin; email delivery is out of scope for the prototype.
    invite_url: str


class InvitePreview(BaseModel):
    project_name: str
    email: str
    role: Role
    user_exists: bool


class InviteAcceptIn(BaseModel):
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=1000)
    display_name: str = Field(default="", max_length=200)


class AuditOut(ORMModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    action: str
    target_type: str | None
    target_id: str | None
    details: dict
    ip: str | None
    created_at: datetime
