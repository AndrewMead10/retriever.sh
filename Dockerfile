###############################
# Backend OpenAPI export stage
###############################
FROM python:3.11-slim as backend-openapi
WORKDIR /app

# Install build dependencies for llama-cpp-python
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    cmake \
 && rm -rf /var/lib/apt/lists/*

RUN pip install uv

COPY backend/ ./backend
WORKDIR /app/backend

RUN uv sync
ENV JWT_SECRET=build-secret \
    ACCESS_TOKEN_TTL_MINUTES=15 \
    REFRESH_TOKEN_TTL_DAYS=30
RUN uv run python -m app.scripts.export_openapi

###############################
# Frontend build stage
###############################
FROM node:18-alpine as frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
# Copy OpenAPI spec generated from backend source and generate TS types
COPY --from=backend-openapi /app/backend/openapi.json /app/frontend/openapi.json
RUN npm run gen:types
RUN npm run build

###############################
# Python backend stage
###############################
FROM python:3.11-slim as backend
WORKDIR /app

# Install curl for healthchecks and build dependencies for llama-cpp-python
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    g++ \
    make \
    cmake \
 && rm -rf /var/lib/apt/lists/*

# Install UV for faster dependency management
RUN pip install uv

# Copy backend project files and install dependencies
COPY backend/ ./backend
WORKDIR /app/backend

RUN uv sync

# Copy built frontend files into FastAPI static dir
COPY --from=frontend-builder /app/frontend/dist /app/backend/app/static

# Create data directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 5656

# Health check (use liveness endpoint)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -fsS http://localhost:5656/livez || exit 1

# Run migrations and start application
CMD ["sh", "-c", "mkdir -p data && uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port 5656"]
