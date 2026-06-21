###############################
# Frontend build stage
###############################
FROM node:20-alpine as frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
# Generate TS types from the backend OpenAPI spec committed by CI/dev workflow.
COPY backend/openapi.json /app/frontend/openapi.json
RUN npm run gen:types
RUN npm run build

###############################
# Python backend stage
###############################
FROM python:3.11-slim as backend
WORKDIR /app

# Install curl for healthchecks and pg_dump for scheduled PostgreSQL backups.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    curl \
    postgresql-client \
 && rm -rf /var/lib/apt/lists/*

# Install UV for faster dependency management
RUN pip install uv

# Copy backend project files and install dependencies
COPY backend/ ./backend
WORKDIR /app/backend

RUN uv sync --locked

# Copy built frontend files into FastAPI static dir
COPY --from=frontend-builder /app/backend/app/static /app/backend/app/static

# Create data directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 5656

# Health check (use liveness endpoint)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl --fail --silent --show-error --connect-timeout 1 --max-time 3 http://localhost:5656/livez || exit 1

# Run migrations and start application
CMD ["sh", "-c", "mkdir -p data && uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port 5656 --workers ${WEB_CONCURRENCY:-2} --timeout-keep-alive 5"]
