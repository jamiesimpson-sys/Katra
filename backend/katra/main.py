import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from sqlalchemy import text

from katra.api import auth, invites, projects
from katra.config import get_settings
from katra.db.session import get_sessionmaker
from katra.services.users import bootstrap_admin

log = logging.getLogger("katra")


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
        if request.url.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.get("/api/health", tags=["meta"])
    def health() -> dict[str, str]:
        with get_sessionmaker()() as db:
            db.execute(text("SELECT 1"))
        return {"status": "ok"}

    app.include_router(auth.router)
    app.include_router(invites.router)
    app.include_router(projects.router)
    return app


app = create_app()
