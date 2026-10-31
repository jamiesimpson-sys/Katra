import os

# Point the app at the test database before anything imports katra.config.
os.environ.setdefault(
    "KATRA_DATABASE_URL",
    os.environ.get(
        "KATRA_TEST_DATABASE_URL", "postgresql+psycopg://katra:test@localhost:5433/katra_test"
    ),
)
os.environ["KATRA_BOOTSTRAP_ADMIN_EMAIL"] = ""
os.environ["KATRA_LLM_PROVIDER"] = "fake"
os.environ["KATRA_EMBEDDING_PROVIDER"] = "fake"

import uuid  # noqa: E402
from collections.abc import Callable, Iterator  # noqa: E402
from dataclasses import dataclass  # noqa: E402

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from katra.api.auth import login_limiter  # noqa: E402
from katra.auth.security import hash_password  # noqa: E402
from katra.config import get_settings  # noqa: E402
from katra.db.session import get_engine, get_sessionmaker  # noqa: E402
from katra.main import create_app  # noqa: E402
from katra.models import Base, Project, ProjectMember, Role, User  # noqa: E402

PASSWORD = "correct horse battery"
BACKEND_DIR = os.path.dirname(os.path.dirname(__file__))


def alembic_config() -> Config:
    cfg = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BACKEND_DIR, "katra/db/migrations"))
    cfg.attributes["database_url"] = get_settings().database_url.get_secret_value()
    return cfg


@pytest.fixture(scope="session", autouse=True)
def migrated_db() -> Iterator[None]:
    with get_engine().begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
    command.upgrade(alembic_config(), "head")
    yield


@pytest.fixture(autouse=True)
def clean_db() -> Iterator[None]:
    yield
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with get_engine().begin() as conn:
        # Bypass the audit log's append-only triggers for test cleanup only.
        conn.execute(text("SET LOCAL session_replication_role = replica"))
        conn.execute(text(f"TRUNCATE {tables} CASCADE"))
    login_limiter.reset()


@pytest.fixture
def db() -> Iterator[Session]:
    with get_sessionmaker()() as session:
        yield session


@pytest.fixture(scope="session")
def app():  # noqa: ANN201
    return create_app()


@pytest.fixture
def anon(app) -> TestClient:  # noqa: ANN001
    return TestClient(app, base_url="https://testserver")


def make_user(db: Session, email: str, *, staff: bool = False) -> User:
    user = User(
        email=email,
        display_name=email.split("@")[0],
        password_hash=hash_password(PASSWORD),
        is_staff=staff,
    )
    db.add(user)
    db.commit()
    return user


def login(app, email: str, password: str = PASSWORD) -> TestClient:  # noqa: ANN001
    client = TestClient(app, base_url="https://testserver")
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    client.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    return client


@pytest.fixture
def client_for(app) -> Callable[[str], TestClient]:  # noqa: ANN001
    return lambda email: login(app, email)


@dataclass
class World:
    """Two projects. Project A has an admin, owner and viewer; `outsider` is admin of B only."""

    project_a: Project
    project_b: Project
    clients: dict[str, TestClient]
    users: dict[str, User]


@pytest.fixture
def world(db: Session, app) -> World:  # noqa: ANN001
    users = {
        "admin": make_user(db, "admin@example.com", staff=True),
        "owner": make_user(db, "owner@example.com"),
        "viewer": make_user(db, "viewer@example.com"),
        "outsider": make_user(db, "outsider@example.com", staff=True),
    }
    a = Project(name="Acme IT", module_id="diligence_ready")
    b = Project(name="Other Co", module_id="diligence_ready")
    db.add_all([a, b])
    db.flush()
    db.add_all(
        [
            ProjectMember(project_id=a.id, user_id=users["admin"].id, role=Role.ADMIN),
            ProjectMember(project_id=a.id, user_id=users["owner"].id, role=Role.OWNER),
            ProjectMember(project_id=a.id, user_id=users["viewer"].id, role=Role.VIEWER),
            ProjectMember(project_id=b.id, user_id=users["outsider"].id, role=Role.ADMIN),
        ]
    )
    db.commit()
    clients = {name: login(app, u.email) for name, u in users.items()}
    clients["anonymous"] = TestClient(app, base_url="https://testserver")
    return World(project_a=a, project_b=b, clients=clients, users=users)


def random_id() -> str:
    return str(uuid.uuid4())
