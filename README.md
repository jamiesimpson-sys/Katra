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

## Deploy to Render (works from a phone)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/jamiesimpson-sys/Katra)

1. Tap the button and sign in to Render with GitHub. Allow Render to access this repo when asked.
2. Render reads [`render.yaml`](render.yaml). Fill in the two prompted values:
   - `KATRA_BOOTSTRAP_ADMIN_EMAIL`: your login email.
   - `KATRA_BOOTSTRAP_ADMIN_PASSWORD`: at least 10 characters.
3. Tap **Deploy Blueprint**. The first build takes about 5–10 minutes. Then open the `katra` service and tap its `…onrender.com` URL.

This creates one web service (API, frontend and background worker in one container) and a Postgres database. Render provides HTTPS. Notes on the free plan:
- The service sleeps after about 15 minutes idle, so the first visit afterwards takes up to about a minute.
- Free databases expire after 30 days. Switch both `plan:` values to paid ones for anything longer-lived.
- Every push to the default branch redeploys.

## Admin data browser

Superusers can browse all tables at `/admin` (there's an **Admin** link in the header). The bootstrap
admin is a superuser automatically. Most tables are read-only. See
[`docs/milestones/M2.5.md`](docs/milestones/M2.5.md).

## Develop

```sh
make test    # backend (pytest against a throwaway Postgres) + frontend (Vitest)
make lint
```

- **Backend:** `backend/`, Python 3.12, managed with [uv](https://docs.astral.sh/uv/). Run `uv sync`, then `uv run uvicorn katra.main:app --reload` with `KATRA_DATABASE_URL` set.
- **Frontend:** `frontend/`. Run `npm install`, then `npm run dev`. The dev server proxies `/api` to `localhost:8000`.
- **Create a staff user:** `docker compose exec api python -m katra.cli create-admin --email you@example.com`
