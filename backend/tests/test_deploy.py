from fastapi.testclient import TestClient

from katra.config import Settings
from katra.main import create_app, mount_spa


def test_hosting_database_urls_use_psycopg():
    for url in ("postgres://u:p@h:5432/db", "postgresql://u:p@h:5432/db"):
        s = Settings(database_url=url)
        assert s.database_url.get_secret_value() == "postgresql+psycopg://u:p@h:5432/db"


def test_invite_links_use_request_host_when_unconfigured(world):
    r = world.clients["admin"].post(
        f"/api/projects/{world.project_a.id}/invites",
        json={"email": "n@example.com", "role": "owner"},
    )
    assert r.json()["invite_url"].startswith("https://testserver/invite/")


def test_spa_serving(tmp_path):
    (tmp_path / "index.html").write_text("<title>Katra</title>")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app-123.js").write_text("console.log(1)")
    (tmp_path.parent / "secret.txt").write_text("nope")

    app = create_app()
    mount_spa(app, tmp_path)
    client = TestClient(app, base_url="https://testserver")

    shell = client.get("/projects/abc/members")
    assert shell.status_code == 200 and "Katra" in shell.text
    assert "Content-Security-Policy" in shell.headers
    assert "Strict-Transport-Security" in shell.headers

    asset = client.get("/assets/app-123.js")
    assert asset.text == "console.log(1)" and "immutable" in asset.headers["Cache-Control"]

    # Unknown API paths stay JSON 404s instead of returning the app shell.
    assert client.get("/api/nope").status_code == 404
    assert client.get("/api/nope").json() == {"detail": "Not Found"}
    # No escaping the static directory.
    assert "nope" not in client.get("/..%2Fsecret.txt").text
    assert "nope" not in client.get("/../secret.txt").text


def test_health_reports_live_commit(anon, monkeypatch):
    assert anon.get("/api/health").json() == {"status": "ok", "commit": "dev"}
    monkeypatch.setenv("RENDER_GIT_COMMIT", "03434f5abcdef0123")
    assert anon.get("/api/health").json()["commit"] == "03434f5"
