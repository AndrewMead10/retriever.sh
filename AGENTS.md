# retriever.sh

A comprehensive full-stack service template with FastAPI, React, and modern development practices. This template provides authentication and production-ready features out of the box. If you are seeing this in an actual project, be sure to remove it and replace it with a description of what you are working on.

## 📋 Project Notes

> **For AI Assistants**: This is a **LIVING SECTION** that serves as your notes about the specific project being built with this template. Use this space to capture and maintain context about what the user is building, their goals, technical decisions, progress, and any other relevant information that will help you provide better assistance. Update this section continuously as you learn more about the project.

### Notes About This Project

- Building a multi-tenant RAG platform evolved from `../vector-lab-rag`, keeping existing hybrid retrieval and embedding configurability while productizing the experience.
- Pricing refresh (Nov 5, 2025): Tinkering ($5/mo; 1 QPS; 3 projects; ≈10k vectors/project), Building ($20/mo; 10 QPS; 20 projects; ≈100k vectors/project), and Scale ($50/mo; 100 QPS; unlimited projects; 250k vectors per project). Accounts start on Tinkering and can self-upgrade to Building or Scale without contacting sales.
- Backend work in progress: added account/plan data model, seeded plan defaults (Tinkering/Building/Scale), per-project pgvector namespaces in PostgreSQL, API-first ingestion/query endpoints using per-project keys, Polar checkout/portal/webhook scaffolding, and persistent usage counters + request-level limits without Redis. Top-ups have been removed; capacity only scales via plan changes. Frontend now includes a projects dashboard with plan usage, upgrade affordances, project creation dialog, and theme toggle. Polar credential configuration, production webhook hardening, and deeper e2e tests still pending.
- Frontend auth hook now accepts `useAuth({ fetchUser: false })` to skip eager `/api/auth/me` calls on public screens like login/register, preventing refresh loops while unauthenticated. Navbar uses current route to disable the fetch on `/auth/*` paths.
- Polar config bug: FastAPI settings now read `POLAR_PRODUCT_TINKERING_ID`/`POLAR_PRODUCT_BUILDING_ID`/`POLAR_PRODUCT_SCALE_ID` via `AliasChoices` so plan flows pick up Polar product UUIDs correctly in Docker deployments.
- Billing UX refresh (Nov 9, 2025): subscription CTAs on projects route users to `/pricing` to pick Tinkering/Building/Scale plans directly; legacy `/api/billing/upgrade`, `/api/billing/topup`, and `/api/billing/enterprise` endpoints and UI entry points were removed in favor of self-serve plan changes.

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
- **Database**: PostgreSQL (pgvector) with Alembic migrations
- **Deployment**: Docker and Docker Compose ready

## Quick Start

### Development Setup

The primary database runs in PostgreSQL (default local URI `postgresql+psycopg://postgres:postgres@localhost:5432/rag`).

1. **Access the application**:
The app in development will have a seperate frontend and backend running, but for deployments, we will build and server the frontend from the backend, allowing for a single container deployment.
   - Frontend: http://localhost:3000 (development)
   - Backend API: http://localhost:5656
   - API Docs: http://localhost:5656/docs

### Production Deployment

1. **Using Docker Compose**:
   ```bash
   cp .env.example .env
   # Edit .env with production values
   docker-compose up -d
   ```

2. **Access the application**:
   - Application: http://localhost:5656
   - API Docs: http://localhost:5656/docs

### Updating Production Deployment

For updating a running production deployment:

```bash
# Quick update (uses Docker cache)
./update-deployment.sh

# Full rebuild (no cache, slower but ensures clean build)
./update-deployment.sh --full-rebuild
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
// Enhanced fetch with automatic token refresh
async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const response = await fetch(url, options)

  // If we get a 401, try refreshing the token and retry once
  if (response.status === 401 && url !== '/auth/refresh') {
    try {
      await fetch('/auth/refresh', { method: 'POST' })
      // Retry the original request
      return await fetch(url, options)
    } catch (refreshError) {
      // If refresh fails, redirect to login
      window.location.href = '/auth/login'
      throw new Error('Authentication failed')
    }
  }

  return response
}
```

**How it works:**
1. Intercepts all API calls that return 401 (Unauthorized)
2. Automatically calls the `/auth/refresh` endpoint to get a new access token
3. Retries the original request with the new token
4. If refresh fails, redirects user to login page

**Usage guidelines:**
- Use `fetchWithAuth()` for authenticated API calls. It surfaces 401 errors without automatic refresh.
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

- Frontend `fetchWithAuth` implements a refresh lock so only one `/auth/refresh` runs at a time and other 401s wait, then retry once.
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
