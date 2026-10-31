"""Role x endpoint matrix, including cross-project and anonymous access.

Every project-scoped endpoint must appear here (test_route_inventory checks this).
"""

import pytest

from tests.conftest import random_id

ADMIN, OWNER, VIEWER = "admin", "owner", "viewer"
ALL = {ADMIN, OWNER, VIEWER}

# (method, path template, body, roles allowed)
ENDPOINTS = [
    ("GET", "/api/projects/{pid}", None, ALL),
    ("GET", "/api/projects/{pid}/module", None, ALL),
    ("GET", "/api/projects/{pid}/members", None, {ADMIN}),
    ("DELETE", "/api/projects/{pid}/members/{rid}", None, {ADMIN}),
    ("GET", "/api/projects/{pid}/invites", None, {ADMIN}),
    ("POST", "/api/projects/{pid}/invites", {"email": "n@example.com", "role": "viewer"}, {ADMIN}),
    ("DELETE", "/api/projects/{pid}/invites/{rid}", None, {ADMIN}),
    ("GET", "/api/projects/{pid}/audit", None, {ADMIN}),
]

MATRIX_PATHS = {(m, p) for m, p, _, _ in ENDPOINTS}


def _call(client, method, path, body):
    return client.request(method, path, json=body)


@pytest.mark.parametrize(("method", "path", "body", "allowed"), ENDPOINTS)
@pytest.mark.parametrize("who", [ADMIN, OWNER, VIEWER, "outsider", "anonymous"])
def test_matrix(world, who, method, path, body, allowed):
    url = path.format(pid=world.project_a.id, rid=random_id())
    r = _call(world.clients[who], method, url, body)

    if who == "anonymous":
        assert r.status_code == 401
    elif who == "outsider":
        # Non-members can't tell whether the project exists.
        assert r.status_code == 404
        assert r.json()["detail"] == "Project not found"
    elif who in allowed:
        # Allowed through the guard (a 404 here would be for the random sub-resource id).
        assert r.status_code not in (401, 403), r.text
        if "{rid}" not in path:
            assert r.status_code < 400, r.text
    else:
        assert r.status_code == 403


def test_unknown_project_is_404_even_for_staff(world):
    r = world.clients["admin"].get(f"/api/projects/{random_id()}")
    assert r.status_code == 404


def test_cross_project_sub_resources_are_not_reachable(world, db):
    """An admin of project B can't revoke project A's invite through project B's URL."""
    a_admin, b_admin = world.clients["admin"], world.clients["outsider"]
    r = a_admin.post(
        f"/api/projects/{world.project_a.id}/invites",
        json={"email": "target@example.com", "role": "owner"},
    )
    invite_id = r.json()["id"]
    r = b_admin.delete(f"/api/projects/{world.project_b.id}/invites/{invite_id}")
    assert r.status_code == 404
    invites = a_admin.get(f"/api/projects/{world.project_a.id}/invites").json()
    assert invites[0]["revoked_at"] is None
