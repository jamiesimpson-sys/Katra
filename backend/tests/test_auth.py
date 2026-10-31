from fastapi.testclient import TestClient
from sqlalchemy import select

from katra.models import AuditLog
from tests.conftest import PASSWORD, make_user


def test_login_me_logout(db, anon: TestClient):
    make_user(db, "jamie@example.com", staff=True)

    r = anon.post("/api/auth/login", json={"email": "Jamie@Example.com", "password": PASSWORD})
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["email"] == "jamie@example.com"
    assert body["user"]["is_staff"] is True
    assert "password_hash" not in body["user"]

    cookie = r.headers["set-cookie"]
    assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=lax" in cookie

    assert anon.get("/api/auth/me").status_code == 200

    # Logout is a mutating request, so it needs the CSRF token.
    assert anon.post("/api/auth/logout").status_code == 403
    r = anon.post("/api/auth/logout", headers={"X-CSRF-Token": body["csrf_token"]})
    assert r.status_code == 204
    assert anon.get("/api/auth/me").status_code == 401


def test_bad_credentials_are_indistinguishable(db, anon: TestClient):
    make_user(db, "jamie@example.com")
    wrong_pw = anon.post("/api/auth/login", json={"email": "jamie@example.com", "password": "nope"})
    no_user = anon.post("/api/auth/login", json={"email": "ghost@example.com", "password": "nope"})
    assert wrong_pw.status_code == no_user.status_code == 401
    assert wrong_pw.json() == no_user.json()


def test_login_is_rate_limited(db, anon: TestClient):
    make_user(db, "jamie@example.com")
    for _ in range(10):
        anon.post("/api/auth/login", json={"email": "jamie@example.com", "password": "nope"})
    r = anon.post("/api/auth/login", json={"email": "jamie@example.com", "password": PASSWORD})
    assert r.status_code == 429


def test_logins_are_audited(db, anon: TestClient):
    user = make_user(db, "jamie@example.com")
    anon.post("/api/auth/login", json={"email": "jamie@example.com", "password": "nope"})
    anon.post("/api/auth/login", json={"email": "jamie@example.com", "password": PASSWORD})
    actions = db.scalars(select(AuditLog.action).where(AuditLog.user_id == user.id)).all()
    assert sorted(actions) == ["auth.login", "auth.login_failed"]


def test_inactive_user_cannot_log_in(db, anon: TestClient):
    user = make_user(db, "gone@example.com")
    user.is_active = False
    db.commit()
    r = anon.post("/api/auth/login", json={"email": "gone@example.com", "password": PASSWORD})
    assert r.status_code == 401


def test_csrf_token_from_another_session_is_rejected(db, app, client_for):
    make_user(db, "a@example.com", staff=True)
    make_user(db, "b@example.com", staff=True)
    a, b = client_for("a@example.com"), client_for("b@example.com")
    a.headers["X-CSRF-Token"] = b.headers["X-CSRF-Token"]
    r = a.post("/api/projects", json={"name": "X", "module_id": "diligence_ready"})
    assert r.status_code == 403
