"""The /admin data browser: superusers only, secrets hidden, mostly read-only, audited."""

import pytest
from sqlalchemy import select

from katra import cli
from katra.admin import VIEWS
from katra.models import AuditLog, KnowledgeItem, User
from katra.services.users import ensure_superuser
from tests.conftest import login, make_user

IDENTITY = {v.model: v.identity for v in VIEWS}


@pytest.fixture
def superuser(db, app):
    user = make_user(db, "root@example.com", staff=True)
    user.is_superuser = True
    db.commit()
    return login(app, user.email)


def test_anonymous_is_sent_to_login(anon):
    r = anon.get("/admin/", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "/login"


@pytest.mark.parametrize("who", ["admin", "owner", "viewer", "outsider"])
def test_non_superusers_are_refused(world, who):
    """Staff (brokers) included: the admin sees every project, so it is superuser-only."""
    r = world.clients[who].get(f"/admin/{IDENTITY[User]}/list", follow_redirects=False)
    assert r.status_code == 403


def test_inactive_superuser_is_refused(db, superuser):
    user = db.scalar(select(User).where(User.email == "root@example.com"))
    user.is_active = False
    db.commit()
    assert superuser.get("/admin/", follow_redirects=False).status_code == 302


@pytest.mark.parametrize("view", VIEWS, ids=lambda v: v.identity)
def test_every_table_lists_for_superusers(world, superuser, view):
    r = superuser.get(f"/admin/{view.identity}/list")
    assert r.status_code == 200, r.text[:300]


def test_secrets_are_never_shown(world, db, superuser):
    user = world.users["owner"]
    pages = [
        superuser.get(f"/admin/{IDENTITY[User]}/list").text,
        superuser.get(f"/admin/{IDENTITY[User]}/details/{user.id}").text,
    ]
    for html in pages:
        assert user.password_hash not in html
        assert "password_hash" not in html.lower().replace(" ", "_")


def test_read_only_tables_cannot_be_edited_or_deleted(world, superuser):
    identity = IDENTITY[KnowledgeItem]
    assert superuser.get(f"/admin/{identity}/create").status_code in (403, 404, 405)
    assert superuser.get(f"/admin/{identity}/edit/1").status_code in (403, 404, 405)
    r = superuser.delete(f"/admin/{identity}/delete?pks=1")
    assert r.status_code in (403, 404, 405)


def test_no_table_allows_create_delete_or_export():
    for view in VIEWS:
        assert not view.can_create and not view.can_delete and not view.can_export, view.identity


def test_superuser_can_edit_safe_fields_only(world, db, superuser):
    owner = world.users["owner"]
    r = superuser.post(
        f"/admin/{IDENTITY[User]}/edit/{owner.id}",
        data={
            "display_name": "Sam Owner",
            "is_active": "y",
            "is_superuser": "y",
            "email": "x@x.com",
        },
        follow_redirects=False,
    )
    assert r.status_code in (302, 303), r.text[:500]
    db.expire_all()
    owner = db.get(User, owner.id)
    assert owner.display_name == "Sam Owner"
    assert owner.is_superuser is False  # not an editable field
    assert owner.email == "owner@example.com"

    entry = db.scalar(select(AuditLog).where(AuditLog.action == "admin.update"))
    assert entry is not None
    assert entry.target_type == IDENTITY[User] and entry.target_id == str(owner.id)
    assert "display_name" in entry.details["fields"]
    assert "Sam Owner" not in str(entry.details)  # field names only, never values


def test_admin_page_views_are_audited(world, db, superuser):
    superuser.get(f"/admin/{IDENTITY[User]}/list")
    paths = db.scalars(select(AuditLog.details).where(AuditLog.action == "admin.view")).all()
    assert {"path": f"/admin/{IDENTITY[User]}/list"} in paths


def test_bootstrap_admin_becomes_superuser(db):
    user = make_user(db, "jamie@example.com", staff=True)
    assert ensure_superuser(db, "JAMIE@example.com") is True
    db.refresh(user)
    assert user.is_superuser
    assert ensure_superuser(db, "jamie@example.com") is False  # already set
    assert ensure_superuser(db, None) is False


def test_cli_grants_and_revokes_superuser(db):
    user = make_user(db, "ops@example.com")
    assert cli.main(["grant-superuser", "--email", "ops@example.com"]) == 0
    db.refresh(user)
    assert user.is_superuser
    assert cli.main(["revoke-superuser", "--email", "ops@example.com"]) == 0
    db.refresh(user)
    assert not user.is_superuser
    assert cli.main(["grant-superuser", "--email", "nobody@example.com"]) == 1


def test_me_reports_superuser_flag(superuser):
    assert superuser.get("/api/auth/me").json()["user"]["is_superuser"] is True


@pytest.mark.parametrize("view", VIEWS, ids=lambda v: v.identity)
def test_every_view_hides_secret_columns(view):
    from katra.admin import SECRET_COLUMNS

    secrets = {c.key for c in view.model.__table__.columns} & SECRET_COLUMNS
    for attr in ("column_exclude_list", "column_details_exclude_list"):
        hidden = {getattr(c, "key", c) for c in getattr(view, attr)}
        assert secrets <= hidden, f"{view.identity}.{attr} must hide {secrets - hidden}"
    if view.column_list:
        shown = {getattr(c, "key", c) for c in view.column_list}
        assert not (shown & SECRET_COLUMNS)


def test_secret_only_tables_have_no_view():
    models = {v.model.__tablename__ for v in VIEWS}
    assert "auth_sessions" not in models and "project_keys" not in models


def test_admin_logout_ends_the_session(superuser):
    r = superuser.get("/admin/logout", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "/login"
    assert superuser.get("/api/auth/me").status_code == 401
