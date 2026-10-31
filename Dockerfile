# All-in-one image for hosted deploys (e.g. Render): the API also serves the built SPA,
# and the job worker runs alongside it. The host terminates HTTPS.
# For local development use docker-compose.yml instead.

FROM node:22-alpine AS frontend
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    KATRA_STATIC_DIR=/app/static \
    KATRA_MODULES_DIR=/app/modules

RUN pip install --no-cache-dir uv==0.11.32 \
    && useradd --create-home --uid 1000 katra

WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/alembic.ini ./
COPY backend/katra ./katra
COPY modules ./modules
RUN uv sync --frozen --no-dev
COPY --from=frontend /app/dist ./static

USER katra
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && (python -m katra.jobs.worker &) && exec uvicorn katra.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
