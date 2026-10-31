.PHONY: env up down logs test test-backend test-frontend lint testdb

TEST_DB_URL ?= postgresql+psycopg://katra:test@localhost:5433/katra_test

env:
	@./scripts/init-env.sh

## Start the whole stack (creates .env on first run).
up: env
	docker compose up -d --build --wait
	@echo ""
	@echo "Katra is running at https://localhost:$$(grep -E '^KATRA_HTTPS_PORT=' .env | cut -d= -f2)"
	@echo "Sign in with the admin credentials in .env (local certificate: accept the browser warning)."

down:
	docker compose down

logs:
	docker compose logs -f

## Throwaway Postgres+pgvector for the backend tests.
testdb:
	@docker start katra-testdb >/dev/null 2>&1 || docker run -d --name katra-testdb \
		-e POSTGRES_USER=katra -e POSTGRES_PASSWORD=test -e POSTGRES_DB=katra_test \
		-p 5433:5432 pgvector/pgvector:pg16 >/dev/null
	@until docker exec katra-testdb pg_isready -U katra -d katra_test >/dev/null 2>&1; do sleep 1; done

test: test-backend test-frontend

test-backend: testdb
	cd backend && KATRA_DATABASE_URL=$(TEST_DB_URL) uv run pytest -q

test-frontend:
	cd frontend && npm test

lint:
	cd backend && uv run ruff check katra tests && uv run ruff format --check katra tests
	cd frontend && npm run typecheck
