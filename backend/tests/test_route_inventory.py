"""Fails if any project-scoped route skips the RBAC dependency or the authorization matrix."""

from fastapi.routing import APIRoute

from katra.main import create_app
from tests.test_authorization_matrix import MATRIX_PATHS


def _has_rbac(dependant) -> bool:
    for dep in dependant.dependencies:
        if getattr(dep.call, "__katra_rbac__", False) or _has_rbac(dep):
            return True
    return False


def _project_routes():
    for route in create_app().routes:
        if isinstance(route, APIRoute) and "{project_id}" in route.path:
            for method in route.methods:
                yield method, route


def test_every_project_route_has_rbac_dependency():
    missing = [f"{m} {r.path}" for m, r in _project_routes() if not _has_rbac(r.dependant)]
    assert not missing, f"Project routes without require_project_role: {missing}"


def test_every_project_route_is_in_the_authorization_matrix():
    def normalise(path: str) -> str:
        return (
            path.replace("{project_id}", "{pid}")
            .replace("{user_id}", "{rid}")
            .replace("{invite_id}", "{rid}")
        )

    missing = [
        f"{m} {r.path}" for m, r in _project_routes() if (m, normalise(r.path)) not in MATRIX_PATHS
    ]
    assert not missing, f"Add these routes to tests/test_authorization_matrix.py: {missing}"


def test_inventory_detects_unguarded_routes():
    """Sanity check that the inventory would actually catch a missing guard."""
    from fastapi import FastAPI

    app = FastAPI()

    @app.get("/api/projects/{project_id}/leak")
    def leak(project_id: str) -> dict:
        return {}

    route = next(r for r in app.routes if isinstance(r, APIRoute))
    assert not _has_rbac(route.dependant)
