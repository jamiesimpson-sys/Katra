import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from sqlalchemy import text

from katra.api import auth, invites, projects
from katra.config import get_settings
from katra.db.session import get_sessionmaker
from katra.services.users import bootstrap_admin

log = logging.getLogger("katra")

SPA_CSP = (
    "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
    "frame-ancestors 'none'"
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    password = settings.bootstrap_admin_password
    with get_sessionmaker()() as db:
        user = bootstrap_admin(
            db, settings.bootstrap_admin_email, password.get_secret_value() if password else None
        )
        if user:
            log.warning("Created bootstrap admin %s", user.email)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Katra", lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json"
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):  # noqa: ANN001, ANN202
        response: Response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        if request.url.scheme == "https":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
        if request.url.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        else:
            response.headers.setdefault("Content-Security-Policy", SPA_CSP)
        return response

    @app.get("/api/health", tags=["meta"])
    def health() -> dict[str, str]:
        with get_sessionmaker()() as db:
            db.execute(text("SELECT 1"))
        # Render sets RENDER_GIT_COMMIT, so the UI can show which commit is live.
        return {"status": "ok", "commit": os.environ.get("RENDER_GIT_COMMIT", "")[:7] or "dev"}

    app.include_router(auth.router)
    app.include_router(invites.router)
    app.include_router(projects.router)

    static_dir = get_settings().static_dir
    if static_dir:
        mount_spa(app, Path(static_dir))
    return app


def mount_spa(app: FastAPI, root: Path) -> None:
    """Serve the built SPA for single-container deploys (locally, Caddy does this)."""
    root = root.resolve()
    index = root / "index.html"

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(404, "Not Found")
        candidate = (root / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(root):
            # Vite fingerprints asset filenames, so they can be cached for good.
            immutable = candidate.parent.name == "assets"
            headers = {"Cache-Control": "public, max-age=31536000, immutable"} if immutable else {}
            return FileResponse(candidate, headers=headers)
        # Client-side routes (e.g. /projects/123) all load the app shell.
        return FileResponse(index, headers={"Cache-Control": "no-cache"})


app = create_app()
