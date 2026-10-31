from datetime import timedelta

from sqlalchemy import select

from katra.models import AuditLog, Invite, ProjectMember
from katra.models.base import utcnow
from tests.conftest import PASSWORD, make_user


def _invite(client, project_id, email, role):
    r = client.post(f"/api/projects/{project_id}/invites", json={"email": email, "role": role})
    assert r.status_code == 201, r.text
    return r.json()["invite_url"].rsplit("/", 1)[1]


def test_staff_creates_project_and_becomes_admin(db, client_for):
    make_user(db, "broker@example.com", staff=True)
    client = client_for("broker@example.com")
    r = client.post("/api/projects", json={"name": "Acme IT", "module_id": "diligence_ready"})
    assert r.status_code == 201
    assert r.json()["role"] == "admin"
    listed = client.get("/api/projects").json()
    assert [p["name"] for p in listed] == ["Acme IT"]


def test_non_staff_cannot_create_projects(world):
    r = world.clients["owner"].post("/api/projects", json={"name": "X", "module_id": "m"})
    assert r.status_code == 403


def test_project_list_only_shows_memberships(world):
    names = [p["name"] for p in world.clients["outsider"].get("/api/projects").json()]
    assert names == ["Other Co"]


def test_full_invite_flow_for_new_user(world, anon, db):
    pid = world.project_a.id
    token = _invite(world.clients["admin"], pid, "newowner@example.com", "owner")

    preview = anon.get(f"/api/invites/{token}").json()
    assert preview == {
        "project_name": "Acme IT",
        "email": "newowner@example.com",
        "role": "owner",
        "user_exists": False,
    }

    r = anon.post(f"/api/invites/{token}/accept", json={"password": "a new password!"})
    assert r.status_code == 200
    assert r.json()["user"]["is_staff"] is False

    # Signed in, sees the project with the invited role.
    projects = anon.get("/api/projects").json()
    assert [(p["name"], p["role"]) for p in projects] == [("Acme IT", "owner")]

    # Tokens are single-use.
    assert anon.get(f"/api/invites/{token}").status_code == 404
    again = anon.post(f"/api/invites/{token}/accept", json={"password": "a new password!"})
    assert again.status_code == 404


def test_invite_for_existing_user_requires_their_password(world, anon, db):
    make_user(db, "existing@example.com")
    token = _invite(world.clients["admin"], world.project_a.id, "existing@example.com", "viewer")
    assert anon.get(f"/api/invites/{token}").json()["user_exists"] is True

    bad = anon.post(f"/api/invites/{token}/accept", json={"password": "not their password"})
    assert bad.status_code == 401
    ok = anon.post(f"/api/invites/{token}/accept", json={"password": PASSWORD})
    assert ok.status_code == 200


def test_expired_and_revoked_invites_are_rejected(world, anon, db):
    admin = world.clients["admin"]
    pid = world.project_a.id
    expired = _invite(admin, pid, "late@example.com", "owner")
    revoked = _invite(admin, pid, "nope@example.com", "owner")

    db.execute(
        Invite.__table__.update()
        .where(Invite.email == "late@example.com")
        .values(expires_at=utcnow() - timedelta(minutes=1))
    )
    db.commit()
    invite_id = db.scalar(select(Invite.id).where(Invite.email == "nope@example.com"))
    assert admin.delete(f"/api/projects/{pid}/invites/{invite_id}").status_code == 204

    for token in (expired, revoked):
        assert anon.get(f"/api/invites/{token}").status_code == 404


def test_short_passwords_rejected_on_accept(world, anon):
    token = _invite(world.clients["admin"], world.project_a.id, "x@example.com", "owner")
    r = anon.post(f"/api/invites/{token}/accept", json={"password": "short"})
    assert r.status_code == 422


def test_cannot_invite_existing_member(world):
    r = world.clients["admin"].post(
        f"/api/projects/{world.project_a.id}/invites",
        json={"email": "owner@example.com", "role": "viewer"},
    )
    assert r.status_code == 409


def test_admin_removes_member(world, db):
    pid = world.project_a.id
    owner_id = world.users["owner"].id
    admin = world.clients["admin"]
    assert admin.delete(f"/api/projects/{pid}/members/{owner_id}").status_code == 204
    assert db.get(ProjectMember, (pid, owner_id)) is None
    assert world.clients["owner"].get(f"/api/projects/{pid}").status_code == 404
    # Admins can't lock themselves out.
    me = world.users["admin"].id
    assert admin.delete(f"/api/projects/{pid}/members/{me}").status_code == 400


def test_project_views_are_audited(world, db):
    pid = world.project_a.id
    world.clients["viewer"].get(f"/api/projects/{pid}")
    entry = db.scalar(
        select(AuditLog).where(AuditLog.action == "project.view", AuditLog.project_id == pid)
    )
    assert entry is not None
    assert entry.user_id == world.users["viewer"].id
