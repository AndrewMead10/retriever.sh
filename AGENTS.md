# retriever.sh

A comprehensive full-stack service template with FastAPI, React, and modern development practices. This template provides authentication and production-ready features out of the box. If you are seeing this in an actual project, be sure to remove it and replace it with a description of what you are working on.

## 📋 Project Notes

> **For AI Assistants**: This is a **LIVING SECTION** that serves as your notes about the specific project being built with this template. Use this space to capture and maintain context about what the user is building, their goals, technical decisions, progress, and any other relevant information that will help you provide better assistance. Update this section continuously as you learn more about the project.

### Notes About This Project

- Building a multi-tenant RAG platform evolved from `../vector-lab-rag`, keeping existing hybrid retrieval and embedding configurability while productizing the experience.
- Pricing refresh (Nov 5, 2025): Tinkering ($5/mo; 5 QPS; 3 projects; ≈10k vectors/project), Building ($20/mo; 10 QPS; 20 projects; ≈100k vectors/project), and Scale ($50/mo; 100 QPS; unlimited projects; 250k vectors per project). Accounts start on Tinkering and can self-upgrade to Building or Scale without contacting sales.
- Rate limit update (Nov 12, 2025): Tinkering's query/ingest QPS limits both default to 5, and ingest QPS remains enforced server-side but is no longer surfaced in the billing/projects UI.
- Backend work in progress: added account/plan data model, seeded plan defaults (Tinkering/Building/Scale), switched hybrid retrieval to Vespa (shared schema filtered by `project_id` + `document_id`) with PostgreSQL only tracking document metadata, API-first ingestion/query endpoints using per-project keys, Polar checkout/portal/webhook scaffolding, and persistent usage counters + request-level limits without Redis. Top-ups have been removed; capacity only scales via plan changes. Frontend now includes a projects dashboard with plan usage, upgrade affordances, project creation dialog, and theme toggle. Polar credential configuration, production webhook hardening, and deeper e2e tests still pending.
- Frontend auth hook now accepts `useAuth({ fetchUser: false })` to skip eager `/api/auth/me` calls on public screens like login/register, preventing refresh loops while unauthenticated. Navbar uses current route to disable the fetch on `/auth/*` paths.
- useProjects now accepts an `enabled` flag so the navbar only loads `/api/projects/onload` after authentication; this stops public routes like `/` from issuing 401 spam when the user is signed out (Nov 10, 2025).
- Backend now drops a non-HTTPOnly `session_present` cookie alongside auth tokens, letting the frontend detect active sessions and avoid `/api/auth/me` calls entirely when logged out; routes now gate their loaders with this flag (Nov 10, 2025).
- Polar config bug: FastAPI settings now read `POLAR_PRODUCT_TINKERING_ID`/`POLAR_PRODUCT_BUILDING_ID`/`POLAR_PRODUCT_SCALE_ID` via `AliasChoices` so plan flows pick up Polar product UUIDs correctly in Docker deployments.
- Billing UX refresh (Nov 9, 2025): subscription CTAs on projects route users to `/pricing` to pick Tinkering/Building/Scale plans directly; legacy `/api/billing/upgrade`, `/api/billing/topup`, and `/api/billing/enterprise` endpoints and UI entry points were removed in favor of self-serve plan changes.
- Billing page (Nov 9, 2025): `/billing` now mirrors Polar return URLs, shows the same plan/usage data as `/projects`, and links into checkout + the Polar customer portal. `/billing/success`, `/billing/canceled`, and `/billing/portal` share the view but display contextual banners so Polar success/cancel/portal return URLs can be pointed there without custom screens.
- Polar webhook fix (Nov 9, 2025): Polar's SDK exposes the event type under the `TYPE` alias, so webhook handlers now read `event.TYPE`/`by_alias` dumps to correctly process `order.paid` and subscription lifecycle events; prior events were being acknowledged without provisioning plans.
- Polar webhook headers (Nov 10, 2025): `/billing/webhook` now forwards the Standard Webhooks header trio (`webhook-id`, `webhook-timestamp`, `webhook-signature`) with a fallback to `Polar-Signature`, so Polar deliveries like `order.updated` validate instead of erroring with "Missing required headers."
- Vector top-up cleanup (Nov 9, 2025): removed the `VectorTopUp` model/table, the `allow_topups` plan flag, and the associated capacity math so vector limits now depend solely on the active plan plus the new Alembic `0004_remove_vector_topups` migration.
- Per-project vector caps (Nov 17, 2025): `plans.vector_limit` now stores the per-project quota (10k/100k/250k for Tinkering/Building/Scale). The backend enforces caps via `ensure_vector_capacity` without a global total limit, Alembic `0007_per_project_vector_limits` seeds existing rows, and the UI shows the per-project allowance instead of an account total.
- Dialog styling quirk (Nov 17, 2025): the `.dither-border` utility sets `position: relative`, so Radix dialogs now wrap their inner content with the decorative class instead of applying it directly to `DialogContent`; otherwise the modal loses `position: fixed` and renders off-screen.
- Project API keys (Nov 17, 2025): the projects dashboard now surfaces a `[ NEW API KEY ]` action per project that confirms rotation, invalidates the prior ingest key server-side, and reuses the API key reveal dialog that also appears after project creation so users can reliably view/copy the key once per issuance.
- Vespa cutover (Nov 19, 2025): pgvector tables are gone. Document content + embeddings now live in the Vespa app under the `rag_document` schema (deployed from `/vespa`). PostgreSQL keeps IDs + metadata via the new `project_documents` table so API responses still expose numeric `document_id`s.
- Container base image (Nov 10, 2025): Dockerfile now uses `python:3.11-slim` for both backend stages; llama.cpp dependencies are installed via UV from backend `pyproject.toml` for both local dev and production parity.
- Alembic history linearized (Nov 16, 2025): migrations now form a single chain (`0002_account_plan_structures` → `0003_replace_stripe_with_polar` → `0003_postgres_vector_store` → `0004_add_email_verification` → `0004_remove_vector_topups` → `0005_add_active_columns` → `0006_remove_account_tables`) so `alembic upgrade head` no longer errors with "Multiple head revisions."
- Deployment update (Jan 8, 2026): `npm run build` now outputs directly to `backend/app/static`, and production deploys are expected to run `uv run uvicorn app.main:app --reload` without Docker; update flow is pull code, build frontend, then restart uvicorn.
- RAG API simplification (Jan 11, 2026): document `url` and `published_at` fields are removed; ingest now accepts optional `metadata` (stored as JSONB and indexed in Vespa), and responses include `metadata` plus `created_at`.
- Deployment update (Jan 11, 2026): Production uses native uvicorn with `--reload` (managed by systemd `retriever.service`). PostgreSQL and Vespa run in Docker via `docker-compose.yml`. Uvicorn watches for file changes, so `git pull` automatically triggers backend restart. Frontend changes require `npm run build`. No update-deployment.sh script needed.
- Migration auto-run (Jan 11, 2026): `retriever.service` now includes `ExecStartPre` to run `alembic upgrade head` on every service start. For code-only changes, `git pull` is enough (uvicorn auto-restarts). For changes with new migrations, run `sudo systemctl restart retriever` to trigger migration execution.
- Docs download refresh (Feb 7, 2026): `/docs` downloadable `retriever-claude-skill.md` now matches live project-scoped API routes (`/api/rag/projects/{project_id}/...` + `X-Project-Key`) and uses fixed `https://retriever.sh` examples (no base-url env var or deployment section).
- Rate-limit bucket self-heal (Feb 7, 2026): some deployment users were missing `rate_limit_buckets` rows and hit `500 Rate limit bucket missing` during ingest/query. `consume_rate_limit` now auto-creates the missing `query`/`ingest` bucket from the current plan limits, and `apply_plan_limits` now guarantees both bucket types exist when plan settings are applied.
- Vespa project-id type fix (Feb 7, 2026): `projects.id` is UUID (string), so Vespa `rag_document.project_id` was migrated from `int` to `string`; YQL filtering now quotes/escapes project IDs and ingest sends tensor fields as `{"values": [...]}` to avoid Vespa `400` upsert errors on `/api/rag/projects/{project_id}/documents`.
- Detached ORM fix in vector-store cache (Feb 7, 2026): `VectorStoreRegistry` now initializes `VespaVectorStore` with primitive `project_id` strings instead of cached SQLAlchemy `Project` instances, preventing `DetachedInstanceError` during threaded ingest/query operations.
- CORS origin normalization (Feb 7, 2026): preflight `OPTIONS` requests to `/api/rag/projects/{project_id}/query` were returning `400` when deployment origin config drifted (e.g. `www` vs apex). CORS setup now canonicalizes configured origins, adds `FRONTEND_URL`, and auto-expands `www`/apex aliases before initializing `CORSMiddleware`.
- CORS preflight fallback (Feb 7, 2026): to support API access from arbitrary origins/endpoints and avoid strict preflight failures in production proxy chains, backend middleware now short-circuits `OPTIONS` with permissive `Access-Control-Allow-*` headers while retaining standard `CORSMiddleware` for normal requests.
- Logfire query logging fix (Feb 7, 2026): `/api/rag/projects/{project_id}/query` now calls `logfire.info(...)` with keyword fields (`project_id`, `query_length`, etc.) instead of passing a metadata dict as a second positional argument, preventing `TypeError: Logfire.info() takes 2 positional arguments but 3 were given`.
- Stability/tooling cleanup (Feb 7, 2026): duplicate project-name slugging now appends numeric suffixes without UUID math errors, `/readyz` now uses `text("SELECT 1")` and returns HTTP 503 when the DB is unavailable, frontend now has a real ESLint config plus `npm run typecheck`, and AGENTS auth refresh docs were aligned with the actual `/api/auth/refresh` lock/retry behavior.

---

> **Instructions for AI Assistants**: 
> - **Always read this section first** when starting work on the project
> - **Update these notes** whenever you learn something new about the project
> - **Use this context** to make informed decisions and suggestions
> - **Keep notes current** - add new insights and remove outdated information
> - **Be flexible** - adapt the content to whatever information is most relevant for this specific project
> - **Ask questions first** - if you're unsure about any project features, requirements, or implementation details before proceeding with development, ask the user for clarification

## Overview

This template implements a modern full-stack application with:

- **Backend**: FastAPI with SQLAlchemy, JWT authentication, structured logging, and UV for dependency management 
- **Frontend**: Vite, using React with TypeScript, TanStack Router/Query, ShadCN, Tailwind CSS
- **Database**: PostgreSQL (via Docker) + Vespa (via Docker) with Alembic migrations
- **Deployment**: Native uvicorn with `--reload` for auto-restart, frontend assets built into backend static directory

## Quick Start

### Development Setup

The primary database runs in PostgreSQL (default local URI `postgresql+psycopg://postgres:postgres@localhost:5432/rag`).

1. **Access the application**:
The app in development will have a seperate frontend and backend running, but for deployments, we will build and server the frontend from the backend, allowing for a single container deployment.
   - Frontend: http://localhost:3000 (development)
   - Backend API: http://localhost:5656
   - API Docs: http://localhost:5656/docs

### Production Deployment

1. **Build frontend into backend static assets**:
   ```bash
   cd frontend
   npm install
   npm run build
   ```

2. **Run the backend**:
   ```bash
   cd backend
   uv sync
   uv run alembic upgrade head
   uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 5656
   ```

3. **Access the application**:
   - Application: http://localhost:5656
   - API Docs: http://localhost:5656/docs

### Updating Production Deployment

Because uvicorn runs with `--reload`, backend file changes trigger automatic restart.

**Backend code only:**
```bash
git pull  # uvicorn auto-restarts when files change
```

**Backend + new migrations:**
```bash
git pull
sudo systemctl restart retriever  # migrations run on service start
```

**Frontend changes:**
```bash
cd frontend && npm run build
```

## Architecture

### Backend Structure (Pages Pattern)

The backend follows a "pages pattern" where routes mirror frontend pages:

```
backend/app/
├── main.py                 # FastAPI app setup
├── config.py              # Configuration management
├── pages/                 # Page-specific business logic
│   ├── auth/             # Authentication pages 
│   ├── dashboard.py      # Dashboard data endpoints
│   └── admin/           # Admin pages 
├── middleware/          # HTTP middleware
├── database/           # Models and database utilities
└── functions/         # Shared business logic
```
The backend pages should have an onLoad route, which will go and load all of the necessary data from the database and return it to the front end, so that for a given page's load, the backend only needs to be called once. 

Then, ideally, a page will have a single onSubmit route, which handles all of the onSubmission logic for that page. Not every page will necessarily have a single on submit. They could potentially need more than one. So you can add more than one onSubmit for page if needed. Just make sure you call it onSubmit and then something descriptive so we know what it is for.

Pages can have as many helper functions as are needed that are specific to that given page. If a function on a given page is used on other pages, then you should add it to a file in the functions folder.

A single page should be a single file, where the onload, onsubmit(s) and any other functions all reside. you shouldnt need to make multiple files for a single page. you can group file pages into a folder if it makes logical sense (like all admin pages go in the admin folder).

The functions folder is for functions that are shared across multiple pages or are complex pieces of logic that should not be included as a helper function on the pages file.

We want to prevent the unnecessary spamming of functions if possible. Functions should only be made either on a page or in the functions file if they need to be reused across multiple other functions. If we end up having a code block that was previously only used in one spot, but is now in multiple spots, then we should break that out into its own function in the functions file to reuse across the different places that call it. If the function is reused twice on the same page but nowhere else, you can just add it as a helper function in that page file instead of needing to add it to the functions folder.

One-off database queries can just be written directly in a page's onLoad or onSubmit. But if queries end up getting used across multiple places, then add them to a file in the database folder. We should not just have a single crud.py file in the databases folder for all of the database operations. Instead, they should be broken into logical pieces instead.

Always be sure to check the existing functions and database files to see if the function or database query you are making could fit into one of those already instead of needing to make a new one. Once again, we are trying to reduce the amount of unnecessary object-oriented code where we just have functions and files displayed all over the place. We want to keep our code as close to the caller as possible.

### Frontend Structure

The frontend uses TanStack Router for file-based routing:

```
frontend/src/
├── routes/              # TanStack Router pages
│   ├── __root.tsx      # Root layout with auth
│   ├── index.tsx       # Home page
│   ├── dashboard/      # Dashboard page
│   └── auth/          # Authentication pages
├── components/         # Reusable UI components
├── lib/               # API client and utilities
└── hooks/            # Custom React hooks
```

Be sure to use shadcn components when possible, and use tailwind for styling. 

## Key Features

### Frontend Authentication Flow

The frontend implements automatic token refresh using the `fetchWithAuth` function in `frontend/src/lib/api.ts`:

```typescript
let refreshPromise: Promise<void> | null = null

async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const response = await fetch(url, options)

  if (response.status === 401 && url !== '/api/auth/refresh') {
    try {
      if (refreshPromise) {
        await refreshPromise
      } else {
        refreshPromise = fetch('/api/auth/refresh', { method: 'POST' })
          .then((refreshResponse) => {
            if (!refreshResponse.ok) throw new Error('Refresh failed')
          })
          .finally(() => {
            refreshPromise = null
          })
        await refreshPromise
      }
      return await fetch(url, options)
    } catch {
      throw new Error('Authentication failed')
    }
  }

  return response
}
```

**How it works:**
1. Intercepts all API calls that return 401 (Unauthorized)
2. Automatically calls `/api/auth/refresh` to get a new access token
3. Uses a refresh lock so concurrent 401s wait on one refresh request
4. Retries the original request once after refresh
5. If refresh fails, throws an auth error (no automatic redirect)

**Usage guidelines:**
- Use `fetchWithAuth()` for authenticated API calls. It attempts one automatic refresh + retry on 401 responses.
- Use regular `fetch()` for public endpoints (login, register, reset request/confirm).
- Protect routes individually by adding a `beforeLoad` that ensures the user is present; public routes omit it.
- Example (protected route):
  ```ts
  // in routes/projects/index.tsx
  export const Route = createFileRoute('/projects/')({
    beforeLoad: async () => {
      try {
        await queryClient.ensureQueryData({
          queryKey: ['user'],
          queryFn: api.auth.getCurrentUser,
        })
      } catch {
        throw redirect({ to: '/auth/login' })
      }
    },
    component: ProjectsPage,
  })
  ```

### Error Handling & Conventions

- Always raise `HTTPException` with a meaningful `detail` string on errors. Avoid custom error shapes.
- Global exception handler returns only `{ detail, request_id, status_code }` — no `message`.
- Frontend should extract and display `detail` (then set `Error(message)` for UI).
- Use toast notifications for user-facing errors/success (no `alert`). We use `sonner` for toasts.

### Auth Refresh Strategy

- Frontend `fetchWithAuth` implements a refresh lock so only one `/api/auth/refresh` runs at a time and other 401s wait, then retry once.
- Tradeoffs:
  - Pros: avoids duplicate refresh calls and race conditions.
  - Cons: if refresh is slow, concurrent 401s wait behind a single promise, adding slight latency spikes under token expiry.
- Given our page pattern (single `onload` and usually a single `onsubmit`), concurrent 401s are uncommon; the lock is primarily defensive and has negligible impact for typical usage.


## Configuration

All configuration is managed through environment variables and Pydantic settings:

```python
# Key configuration options
JWT_SECRET=              # Required: JWT signing secret
ACCESS_TOKEN_TTL_MINUTES=15
REFRESH_TOKEN_TTL_DAYS=30
ENABLE_USER_REGISTRATION=true
ENABLE_ADMIN_PANEL=true
CORS_ORIGINS=["*"]      # Dev-friendly, restrict in production
FRONTEND_URL=http://localhost:3000
COOKIE_SECURE=false      # Set true in production (HTTPS)
GOOGLE_CLIENT_ID=       # Required for Google OAuth
GOOGLE_CLIENT_SECRET=   # Required for Google OAuth
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
GOOGLE_ALLOWED_DOMAINS=[]  # Optional allowlist, e.g. ["example.com"]
```

### Google OAuth Setup

- Backend exposes `/auth/google/login` (redirect to Google) and `/auth/google/callback` (exchanges code, signs the user in, and redirects to the frontend).
- Users signing in with Google are created automatically if they don't already exist; they receive randomly generated passwords and rely on Google for authentication.
- Configure the Google credentials (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`) in `.env` and in Google Cloud Console. Restrict access with `GOOGLE_ALLOWED_DOMAINS` (JSON array such as `["example.com"]`) if required.
- The frontend login page now includes a **Continue with Google** button. It honors an optional `?redirect=/path` query string and forwards that path through the OAuth flow.

## Database Management

Migrations are done with alebic.

### Backup System

Automatic SQLite backups with optional Cloudflare R2 upload:

```python
# Local backups run daily by default
# Configure R2 for offsite backups:
ENABLE_R2_BACKUP=true
R2_ACCOUNT_ID=your-account-id
R2_BUCKET=your-backup-bucket
```
By default this will be off.

## Development Workflow

### Type Safety (OpenAPI)

- Generate types from the running backend: `cd frontend && npm run gen:types` (fetches `http://localhost:5656/openapi.json`).
- Import request/response types from `src/lib/openapi-types.ts` (e.g., `LoginRequest`, `UserResponse`).
- Keep OpenAPI schemas precise (avoid `additionalProperties: true`). For page aggregates like dashboard, define explicit models on the backend so the spec is strongly typed.

### Adding Authenticated API Endpoints

When adding new authenticated endpoints:

1. **Backend**: Create endpoints that require authentication using `get_current_user` dependency
2. **Frontend**: Use `fetchWithAuth()` in your API client functions to ensure automatic token refresh
3. **Example**:
   ```typescript
   // In frontend/src/lib/api.ts
   async getProtectedData(): Promise<any> {
     const response = await fetchWithAuth('/api/protected-endpoint')
     if (!response.ok) {
       throw new Error('Failed to fetch protected data')
     }
     return response.json()
   }
   ```

> **Note for AI Assistants**: If you identify functionality or patterns not covered in this documentation, please update this AGENTS.md file with the new information to help future development and maintenance.
