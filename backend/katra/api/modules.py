from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from katra.auth.deps import StaffUser
from katra.engine.modules import Module, get_registry

router = APIRouter(prefix="/api/modules", tags=["modules"])


class ModuleSummary(BaseModel):
    id: str
    version: int
    name: str
    description: str
    roles: list[str]
    section_count: int
    question_count: int
    session_length_minutes: int
    target_sessions: int


def summarise(m: Module) -> ModuleSummary:
    return ModuleSummary(
        id=m.id,
        version=m.version,
        name=m.name,
        description=m.description,
        roles=m.roles,
        section_count=len(m.sections),
        question_count=len(m.questions()),
        session_length_minutes=m.session_length_minutes,
        target_sessions=m.target_sessions,
    )


@router.get("", response_model=list[ModuleSummary])
def list_modules(_: StaffUser) -> list[ModuleSummary]:
    return [summarise(m) for m in get_registry().all()]


@router.get("/{module_id}", response_model=Module)
def get_module(module_id: str, _: StaffUser) -> Module:
    module = get_registry().get(module_id)
    if module is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Module not found")
    return module
