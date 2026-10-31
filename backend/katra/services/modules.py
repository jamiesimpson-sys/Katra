from fastapi import HTTPException, status

from katra.engine.modules import Module, get_registry
from katra.models import Project


def module_for_project(project: Project) -> Module:
    """The module a project runs on: its snapshot, or the current file for pre-M2 projects."""
    if project.module_snapshot is not None:
        return Module.model_validate(project.module_snapshot)
    module = get_registry().get(project.module_id)
    if module is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Module {project.module_id!r} is no longer available"
        )
    return module
