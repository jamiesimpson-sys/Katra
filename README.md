# Katra

A prototype of Katra's **Diligence-ready** module. An owner uploads documents and is
interviewed by AI from a question bank. The owner then verifies the captured answers, and
the system produces a sourced diligence report and a Q&A assistant.

- Brief: [`docs/SPEC.md`](docs/SPEC.md)
- Architecture and milestones: [`docs/PLAN.md`](docs/PLAN.md)
- Milestone notes: [`docs/milestones/`](docs/milestones)
- Rules for contributors (human or AI): [`CLAUDE.md`](CLAUDE.md)

## Run it

Requires Docker with Compose v2.

```sh
make up      # first run creates .env with random secrets and prints the admin login
```

Open <https://localhost:8443>. It uses a locally issued certificate, so accept the browser
warning once. `make down` stops the stack; `docker compose down -v` also deletes its data.

## Develop

```sh
make test    # backend (pytest against a throwaway Postgres) + frontend (Vitest)
make lint
```

- **Backend:** `backend/`, Python 3.12, managed with [uv](https://docs.astral.sh/uv/). Run `uv sync`, then `uv run uvicorn katra.main:app --reload` with `KATRA_DATABASE_URL` set.
- **Frontend:** `frontend/`. Run `npm install`, then `npm run dev`. The dev server proxies `/api` to `localhost:8000`.
- **Create a staff user:** `docker compose exec api python -m katra.cli create-admin --email you@example.com`
